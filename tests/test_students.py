from pathlib import Path
from typing import Any, Dict

from apps.orchestrator.student_loop import StudentLoopConfig, StudentLoopRunner
from apps.orchestrator.student_qa import StudentQuizEvaluator
from apps.orchestrator.students import StudentGraderPool

RUBRICS = Path("evals/rubrics.yaml")


def _write_artifact(base: Path, text: str) -> Path:
    path = base / "artifact.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_student_grader_pool_passes_with_keywords(tmp_path: Path) -> None:
    artifact = _write_artifact(
        tmp_path,
        """
# Module 1: Relational Foundations
Learning objectives: explain the relational model and SQL fundamentals.
Assessment: create SQL queries that respect transactions and recovery steps while explaining concurrency.
We contrast distributed databases like Spanner with legacy System R deployments to highlight modern design.
Example: students normalize a schema and answer a review question on locking.
This lecture cites foundational work by Codd (1970) and [System R].
        """.strip(),
    )

    grader = StudentGraderPool.from_yaml(RUBRICS, required_sources=["codd-1970"])
    results = grader.evaluate(artifact)

    assert results["rubric_count"] >= 1
    assert results["overall_score"] >= 0.8
    assert all(item["passed"] for item in results["rubrics"])


def test_student_grader_pool_without_required_sources_does_not_require_defaults(tmp_path: Path) -> None:
    artifact = _write_artifact(
        tmp_path,
        """
# Module 2: From Relational Roots to Modern Warehouses
Learning objectives: cover the relational model, SQL fluency, and concurrency design.
Assessment: compare transaction anomalies and recovery trade-offs in short reflections.
We contrast structured warehouses like Snowflake with Spanner-style distributed systems.
Example: students normalize schemas, then answer review questions on locking and recovery steps.
This lecture cites [modern-db-2024] and recent timeline events to ground the discussion.
        """.strip(),
    )

    grader = StudentGraderPool.from_yaml(RUBRICS)
    results = grader.evaluate(artifact)

    grounding = next(item for item in results["rubrics"] if item["name"].lower() == "grounding")
    assert grounding["passed"], "Grounding rubric should pass when no required_sources are configured"


def test_student_grader_pool_does_not_confuse_sql_with_nosql(tmp_path: Path) -> None:
    artifact = _write_artifact(
        tmp_path,
        """
# Distributed trade-offs without query mention
Relational data models emphasize entity integrity and relational algebra foundations.
NoSQL systems prioritize availability and partition tolerance, illustrated via Spanner deployments.
Transactions and recovery trade-offs appear throughout the lecture, but structured query languages are omitted.
        """.strip(),
    )

    grader = StudentGraderPool.from_yaml(RUBRICS, required_sources=[])
    results = grader.evaluate(artifact)

    coverage = next(item for item in results["rubrics"] if item["name"].lower() == "coverage")
    assert not coverage["passed"], "Coverage rubric should fail when SQL is only referenced via 'NoSQL'"


def test_default_keyword_check_respects_word_boundaries() -> None:
    text = "Learners set goals for the term but do not study relational algebra."
    passed, _ = StudentGraderPool._default_keyword_check("goal", text.lower())
    assert not passed, "Keyword detection should not match substrings within larger words"

    positive_text = "Normalization discussion covers locking and transaction control."
    passed_positive, evidence = StudentGraderPool._default_keyword_check(
        "locking control", positive_text.lower()
    )
    assert passed_positive
    assert evidence in {"locking", "control"}


def test_student_grader_pool_flags_missing_sources(tmp_path: Path) -> None:
    artifact = _write_artifact(
        tmp_path,
        """
# Module 1: Relational Foundations
Learning objectives focus on queries and concurrency, but we intentionally omit citations.
Assessment: describe transactions and runtime behavior.
Distributed storage and recovery trade-offs are mentioned, but no sources are cited.
        """.strip(),
    )

    grader = StudentGraderPool.from_yaml(RUBRICS, required_sources=["codd-1970", "system-r-1976"])
    results = grader.evaluate(artifact)

    assert any(not item["passed"] for item in results["rubrics"])
    failing = [item for item in results["rubrics"] if not item["passed"]]
    assert failing, "Expected at least one rubric failure when sources are missing"


def test_student_quiz_evaluator_detects_keywords(tmp_path: Path) -> None:
    quiz_bank = tmp_path / "quiz.json"
    quiz_bank.write_text(
        """
[
  {
    "id": "quiz-1",
    "prompt": "Explain SQL aggregation",
    "answer_sketch": "SQL query uses GROUP BY and HAVING clauses",
    "learning_objectives": ["sql", "aggregation"],
    "difficulty": "medium"
  }
]
        """.strip(),
        encoding="utf-8",
    )
    lecture = _write_artifact(
        tmp_path,
        """
SQL GROUP BY clauses let us aggregate totals. HAVING filters aggregated rows.
        """.strip(),
    )

    evaluator = StudentQuizEvaluator(quiz_bank_path=quiz_bank, pass_threshold=0.5, question_limit=1)
    result = evaluator.evaluate_path(lecture).as_dict()

    assert result["passed"] == 1
    assert result["pass_rate"] == 1.0
    assert result["questions"][0]["passed"] is True


def test_student_loop_runner_triggers_mutation(tmp_path: Path) -> None:
    lecture = _write_artifact(tmp_path, "Original lecture text")

    class StubGrader:
        def __init__(self) -> None:
            self.calls = 0
            self.payloads = [
                {
                    "overall_score": 0.4,
                    "rubrics": [
                        {"name": "coverage", "passed": False},
                        {"name": "grounding", "passed": False},
                    ],
                },
                {
                    "overall_score": 0.92,
                    "rubrics": [
                        {"name": "coverage", "passed": True},
                        {"name": "grounding", "passed": True},
                    ],
                },
            ]

        def evaluate(self, _path: Path) -> Dict[str, object]:  # type: ignore[override]
            payload = self.payloads[min(self.calls, len(self.payloads) - 1)]
            self.calls += 1
            return payload

    class StubQuiz:
        def __init__(self) -> None:
            self.calls = 0
            self.payloads = [
                {"questions": [{"id": "q1", "passed": False, "score": 0.1}], "pass_rate": 0.0},
                {"questions": [{"id": "q1", "passed": True, "score": 0.9}], "pass_rate": 1.0},
            ]

        def evaluate_path(self, _path: Path) -> Any:
            record = self.payloads[min(self.calls, len(self.payloads) - 1)]
            self.calls += 1

            class _Wrapper:
                def __init__(self, data: Dict[str, Any]) -> None:
                    self.data = data

                def as_dict(self) -> Dict[str, Any]:
                    return self.data

            return _Wrapper(record)

    def _mutation_callback(path: Path, iteration: int, reason):
        note = f"\n\n## Mutation {iteration}\nTriggered due to {reason.failing_rubrics}."
        updated = path.read_text(encoding="utf-8") + note
        path.write_text(updated, encoding="utf-8")
        return path

    runner = StudentLoopRunner(
        grader=StubGrader(),
        quiz_evaluator=StubQuiz(),
        config=StudentLoopConfig(rubric_threshold=0.8, quiz_threshold=0.7, max_mutations=1),
        mutation_callback=_mutation_callback,
    )

    results = runner.run(lecture)
    assert results["status"] == "passing"
    assert results["mutations"] == 1
    assert results["attempts"][0]["triggered_mutation"] is not None


def test_student_loop_runner_respects_individual_rubric_failures(tmp_path: Path) -> None:
    lecture = _write_artifact(tmp_path, "Draft lecture")

    class StubGrader:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate(self, _path: Path) -> Dict[str, Any]:  # type: ignore[override]
            self.calls += 1
            if self.calls == 1:
                return {
                    "overall_score": 0.93,
                    "rubrics": [
                        {"name": "coverage", "passed": True, "score": 1.0},
                        {"name": "grounding", "passed": False, "score": 0.79},
                        {"name": "pedagogy", "passed": True, "score": 1.0},
                    ],
                }
            return {
                "overall_score": 0.95,
                "rubrics": [
                    {"name": "coverage", "passed": True, "score": 1.0},
                    {"name": "grounding", "passed": True, "score": 0.9},
                    {"name": "pedagogy", "passed": True, "score": 0.95},
                ],
            }

    class StubQuiz:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate_path(self, _path: Path) -> Any:
            self.calls += 1

            class _Wrapper:
                def as_dict(self) -> Dict[str, Any]:
                    return {"pass_rate": 1.0, "questions": [{"id": "q1", "passed": True}]}

            return _Wrapper()

    def _mutation_callback(path: Path, iteration: int, reason):
        note = f"\n\n## Mutation {iteration}\nTriggering due to {reason.failing_rubrics}"
        updated = path.read_text(encoding="utf-8") + note
        path.write_text(updated, encoding="utf-8")
        return path

    runner = StudentLoopRunner(
        grader=StubGrader(),
        quiz_evaluator=StubQuiz(),
        config=StudentLoopConfig(rubric_threshold=0.8, quiz_threshold=0.7, max_mutations=1),
        mutation_callback=_mutation_callback,
    )

    results = runner.run(lecture)
    assert results["mutations"] == 1
    assert results["status"] == "passing"
    # Ensure the initial failing rubric is recorded
    assert "grounding" in results["attempts"][0]["triggered_mutation"]["failing_rubrics"]
