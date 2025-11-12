from pathlib import Path

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
