"""Quiz-based student QA evaluators used during Phase E."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


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
        tokens = re.split(r"[^a-z0-9]+", self.answer_sketch.lower())
        filtered = {token for token in tokens if len(token) >= 4}
        return sorted(filtered)


@dataclass(slots=True)
class QuizEvaluation:
    """Structured output summarizing quiz-based checks."""

    questions: List[Dict[str, object]]

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
        }


class StudentQuizEvaluator:
    """Lightweight heuristic QA evaluator based on quiz_bank.json."""

    def __init__(
        self,
        quiz_bank_path: Path,
        *,
        pass_threshold: float = 0.7,
        question_limit: int | None = None,
    ) -> None:
        self.quiz_bank_path = quiz_bank_path
        self.pass_threshold = pass_threshold
        self.question_limit = question_limit
        self.questions = self._load_questions(quiz_bank_path)

    def evaluate_path(self, lecture_path: Path) -> QuizEvaluation:
        text = lecture_path.read_text(encoding="utf-8")
        return self.evaluate_text(text)

    def evaluate_text(self, text: str) -> QuizEvaluation:
        normalized = text.lower()
        question_slice = self._select_questions()
        records: List[Dict[str, object]] = []
        for question in question_slice:
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
        return QuizEvaluation(records)

    # ------------------------------------------------------------------

    def _load_questions(self, quiz_bank_path: Path) -> List[QuizQuestion]:
        if not quiz_bank_path.exists():
            raise FileNotFoundError(f"Quiz bank file {quiz_bank_path} is missing")
        payload = json.loads(quiz_bank_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("quiz_bank.json must contain a list of questions")
        questions: List[QuizQuestion] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            question = QuizQuestion(
                id=str(entry.get("id", "question")),
                prompt=str(entry.get("prompt", "")),
                answer_sketch=str(entry.get("answer_sketch", "")),
                learning_objectives=entry.get("learning_objectives") or [],
                difficulty=entry.get("difficulty"),
            )
            questions.append(question)
        questions.sort(key=lambda item: item.id)
        return questions

    def _select_questions(self) -> Iterable[QuizQuestion]:
        if self.question_limit is None or self.question_limit >= len(self.questions):
            return self.questions
        return self.questions[: self.question_limit]

    @staticmethod
    def _keyword_hits(keywords: Sequence[str], text: str) -> List[str]:
        hits = [keyword for keyword in keywords if keyword and keyword in text]
        return hits


__all__ = ["StudentQuizEvaluator", "QuizEvaluation", "QuizQuestion"]
