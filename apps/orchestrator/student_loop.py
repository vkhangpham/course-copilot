"""Student QA + mutation loop coordination."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

from .student_qa import StudentQuizEvaluator
from .students import StudentGraderPool


@dataclass(slots=True)
class MutationReason:
    failing_rubrics: Sequence[str]
    failing_questions: Sequence[str]
    overall_score: float
    quiz_pass_rate: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "failing_rubrics": list(self.failing_rubrics),
            "failing_questions": list(self.failing_questions),
            "overall_score": self.overall_score,
            "quiz_pass_rate": self.quiz_pass_rate,
        }


@dataclass(slots=True)
class StudentLoopConfig:
    rubric_threshold: float
    quiz_threshold: float
    max_mutations: int


class StudentLoopRunner:
    """Coordinates rubric graders, quiz evaluators, and the mutation loop."""

    def __init__(
        self,
        *,
        grader: StudentGraderPool,
        quiz_evaluator: StudentQuizEvaluator,
        config: StudentLoopConfig,
        mutation_callback: Callable[[Path, int, MutationReason], Path],
    ) -> None:
        self.grader = grader
        self.quiz_evaluator = quiz_evaluator
        self.config = config
        self.mutation_callback = mutation_callback

    def run(self, lecture_path: Path) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        current_path = lecture_path
        status = "passing"
        mutation_count = 0

        for iteration in range(1, self.config.max_mutations + 2):
            rubric_results = self.grader.evaluate(current_path)
            quiz_results = self.quiz_evaluator.evaluate_path(current_path).as_dict()
            decision = self._should_continue(rubric_results, quiz_results)
            attempt_record = {
                "iteration": iteration,
                "rubrics": rubric_results,
                "quiz": quiz_results,
                "triggered_mutation": None,
            }
            attempts.append(attempt_record)

            if not decision:
                status = "passing"
                break

            attempt_record["triggered_mutation"] = decision.as_dict()

            if iteration > self.config.max_mutations:
                status = "max_mutations_reached"
                break

            mutation_count += 1
            current_path = self.mutation_callback(current_path, iteration, decision)

        final_attempt = attempts[-1]
        final_rubrics = final_attempt["rubrics"]
        payload: Dict[str, Any] = {
            "use_students": True,
            "status": status,
            "attempts": attempts,
            "mutations": mutation_count,
            "quiz_threshold": self.config.quiz_threshold,
            "rubric_threshold": self.config.rubric_threshold,
            "overall_score": final_rubrics.get("overall_score"),
            "rubrics": final_rubrics.get("rubrics"),
            "rubric_details": final_rubrics,
            "quiz": final_attempt["quiz"],
        }
        return payload

    # ------------------------------------------------------------------

    def _should_continue(self, rubric_results: Dict[str, Any], quiz_results: Dict[str, Any]) -> MutationReason | None:
        overall_score = float(rubric_results.get("overall_score", 0.0) or 0.0)
        rubric_entries = rubric_results.get("rubrics", []) or []
        has_rubrics = bool(rubric_entries)
        rubric_failures = [entry.get("name", "") for entry in rubric_entries if not entry.get("passed")]
        aggregate_pass = overall_score >= self.config.rubric_threshold
        rubric_pass = aggregate_pass and not rubric_failures if has_rubrics else True

        questions = quiz_results.get("questions") or []
        has_quiz = bool(questions)
        quiz_pass_rate = float(quiz_results.get("pass_rate", 0.0) or 0.0)
        quiz_pass = quiz_pass_rate >= self.config.quiz_threshold if has_quiz else True
        failing_questions = [question.get("id", "") for question in questions if not question.get("passed")]

        grounding_configured, grounding_pass = self._grounding_status(rubric_results)

        checks: List[bool] = []
        if has_rubrics:
            checks.append(rubric_pass)
        if has_quiz:
            checks.append(quiz_pass)
        if grounding_configured:
            checks.append(grounding_pass)

        if not checks:
            return None

        satisfied_checks = sum(1 for flag in checks if flag)
        required = min(2, len(checks))
        if satisfied_checks >= required:
            return None

        return MutationReason(
            failing_rubrics=rubric_failures,
            failing_questions=failing_questions,
            overall_score=overall_score,
            quiz_pass_rate=quiz_pass_rate,
        )

    @staticmethod
    def _grounding_status(rubric_results: Dict[str, Any]) -> tuple[bool, bool]:
        entries = rubric_results.get("rubrics", []) or []
        for entry in entries:
            name = str(entry.get("name", "")).strip().lower()
            if name == "grounding":
                return True, bool(entry.get("passed"))
        return False, True


__all__ = ["StudentLoopRunner", "StudentLoopConfig", "MutationReason"]
