"""Quiz-based student QA evaluators used during Phase E."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .student_settings import students_llm_disabled

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class QuizQuestion:
    """Represents a quiz-bank entry with keyword heuristics."""

    id: str
    prompt: str
    answer_sketch: str
    learning_objectives: Sequence[str] = field(default_factory=list)
    difficulty: str | None = None

    @property
    def keywords(self) -> List[str]:
        tokens = [token for token in re.split(r"[^a-z0-9]+", self.answer_sketch.lower()) if token]
        primary = {token for token in tokens if len(token) >= 4}
        if primary:
            return sorted(primary)
        fallback = {token for token in tokens if len(token) >= 3}
        return sorted(fallback or primary)


@dataclass(slots=True)
class QuizEvaluation:
    """Structured output summarizing quiz-based checks."""

    questions: List[Dict[str, object]]
    engine: str = "heuristic"

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def passed(self) -> int:
        return sum(1 for question in self.questions if question.get("passed"))

    @property
    def pass_rate(self) -> float:
        if not self.questions:
            return 0.0
        return round(self.passed / len(self.questions), 3)

    @property
    def average_score(self) -> float:
        if not self.questions:
            return 0.0
        return round(sum(float(question.get("score", 0.0)) for question in self.questions) / len(self.questions), 3)

    def as_dict(self) -> Dict[str, object]:
        return {
            "questions": self.questions,
            "total_questions": self.total,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "avg_score": self.average_score,
            "engine": self.engine,
        }


class StudentQuizEvaluator:
    """Lightweight heuristic QA evaluator based on quiz definitions."""

    def __init__(
        self,
        quiz_bank_path: Path | None = None,
        *,
        questions: Sequence[QuizQuestion | Mapping[str, Any]] | None = None,
        pass_threshold: float = 0.7,
        question_limit: int | None = None,
        lm: Any | None = None,
    ) -> None:
        if quiz_bank_path is None and questions is None:
            raise ValueError("Provide quiz_bank_path or questions when building StudentQuizEvaluator")
        self.quiz_bank_path = quiz_bank_path
        self.pass_threshold = pass_threshold
        self.question_limit = question_limit
        self._lm = None if students_llm_disabled() else lm
        self.uses_llm = bool(self._lm)
        if questions is not None:
            self.questions = self._coerce_questions(questions)
        else:
            assert self.quiz_bank_path is not None  # appease type-checkers
            self.questions = self._load_questions(self.quiz_bank_path)

    def evaluate_path(self, lecture_path: Path) -> QuizEvaluation:
        text = lecture_path.read_text(encoding="utf-8")
        return self.evaluate_text(text)

    def evaluate_text(self, text: str) -> QuizEvaluation:
        normalized = text.lower()
        question_slice = self._select_questions()
        records: List[Dict[str, object]] = []
        used_llm = False
        attempted_llm = False
        for question in question_slice:
            if self.uses_llm:
                attempted_llm = True
                llm_payload = self._grade_question_with_llm(question, normalized)
                if isinstance(llm_payload, dict):
                    used_llm = True
                    records.append(
                        {
                            "id": question.id,
                            "prompt": question.prompt,
                            "learning_objectives": list(question.learning_objectives),
                            "difficulty": question.difficulty,
                            "score": float(llm_payload.get("score", 0.0)),
                            "passed": bool(llm_payload.get("passed")),
                            "evidence": llm_payload.get("evidence"),
                            "answer": llm_payload.get("answer"),
                            "engine": "llm",
                        }
                    )
                    continue

            hits = self._keyword_hits(question.keywords, normalized)
            score = round(len(hits) / len(question.keywords), 3) if question.keywords else 0.0
            records.append(
                {
                    "id": question.id,
                    "prompt": question.prompt,
                    "learning_objectives": list(question.learning_objectives),
                    "difficulty": question.difficulty,
                    "score": score,
                    "passed": score >= self.pass_threshold,
                    "matched_keywords": hits,
                }
            )
        if used_llm:
            engine = "llm"
        elif attempted_llm:
            engine = "heuristic"
        else:
            engine = "llm" if self.uses_llm else "heuristic"
        return QuizEvaluation(records, engine=engine)

    def _grade_question_with_llm(self, question: QuizQuestion, excerpt: str) -> Dict[str, Any] | None:
        if not self._lm:
            return None

        prompt = dedent(
            f"""
            You are an expert teaching assistant that evaluates quiz questions.

            Quiz question: {question.prompt}
            Expected answer sketch: {question.answer_sketch}

            Read the lecture excerpt and decide whether the question is sufficiently answered.
            Respond with JSON using this schema:
            {{
              "score": number between 0 and 1,
              "passed": true/false,
              "evidence": "short justification",
              "answer": "concise answer you would give"
            }}

            <lecture>
            {excerpt}
            </lecture>
            """
        ).strip()

        try:
            raw = self._lm(prompt=prompt)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Quiz evaluator LM call failed for %s: %s", question.id, exc)
            return None

        text = self._normalize_lm_output(raw)
        return self._extract_json(text)

    # ------------------------------------------------------------------

    def _load_questions(self, quiz_bank_path: Path) -> List[QuizQuestion]:
        if not quiz_bank_path.exists():
            raise FileNotFoundError(f"Quiz bank file {quiz_bank_path} is missing")
        payload = json.loads(quiz_bank_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("quiz_bank.json must contain a list of questions")
        questions = self._coerce_questions(payload)
        questions.sort(key=lambda item: item.id)
        return questions

    def _coerce_questions(
        self,
        entries: Sequence[QuizQuestion | Mapping[str, Any]],
    ) -> List[QuizQuestion]:
        questions: List[QuizQuestion] = []
        for entry in entries:
            if isinstance(entry, QuizQuestion):
                questions.append(entry)
                continue
            if not isinstance(entry, Mapping):
                raise ValueError("Quiz entries must be mappings or QuizQuestion instances")
            questions.append(
                QuizQuestion(
                    id=str(entry.get("id", "question")),
                    prompt=str(entry.get("prompt", "")),
                    answer_sketch=str(entry.get("answer_sketch", "")),
                    learning_objectives=self._coerce_objectives(entry.get("learning_objectives")),
                    difficulty=entry.get("difficulty"),
                )
            )
        if not questions:
            raise ValueError("Quiz payload is empty")
        return questions

    @staticmethod
    def _coerce_objectives(value: Any) -> Sequence[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, Iterable):
            return [str(item) for item in value]
        return []

    def _select_questions(self) -> Iterable[QuizQuestion]:
        if self.question_limit is None or self.question_limit >= len(self.questions):
            return self.questions
        return self.questions[: self.question_limit]

    @staticmethod
    def _keyword_present(text: str, keyword: str) -> bool:
        if not keyword:
            return False
        pattern = rf"\b{re.escape(keyword)}\b"
        return re.search(pattern, text) is not None

    @classmethod
    def _keyword_hits(cls, keywords: Sequence[str], text: str) -> List[str]:
        return [keyword for keyword in keywords if cls._keyword_present(text, keyword)]

    @staticmethod
    def _normalize_lm_output(raw: Any) -> str:
        if isinstance(raw, list):
            return "\n".join(str(part) for part in raw)
        return str(raw)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any] | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None


__all__ = ["StudentQuizEvaluator", "QuizEvaluation", "QuizQuestion"]
