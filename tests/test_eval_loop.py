import json
from pathlib import Path

from typer.testing import CliRunner

from apps.orchestrator.eval_loop import app

runner = CliRunner()


def _write_sample_lecture(path: Path) -> None:
    path.write_text(
        """
# Module 1
Learning objective: Understand the relational model and SQL fundamentals.
We review the relational model, SQL syntax, and discuss transactions, recovery, and concurrency.
Distributed databases like Spanner and classic System R comparisons highlight modern systems.
Assessment: students craft an example SQL query and answer a review question about strict 2PL.
Example question: Why does strict two-phase locking avoid dirty reads?
This module references foundational work (1970) and [System R].
        """.strip(),
        encoding="utf-8",
    )


def test_eval_loop_generates_jsonl(tmp_path: Path) -> None:
    lectures_dir = tmp_path / "lectures"
    lectures_dir.mkdir()
    _write_sample_lecture(lectures_dir / "module.md")

    result = runner.invoke(
        app,
        [
            "--artifacts-dir",
            str(tmp_path),
            "--rubric",
            "evals/rubrics.yaml",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Evaluated 1 artifact" in result.output

    eval_dir = tmp_path / "evaluations"
    files = list(eval_dir.glob("eval-*.jsonl"))
    assert len(files) == 1

    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    assert lines, "Evaluation file should contain at least one record"
    record = json.loads(lines[0])
    assert record["artifact"].endswith("module.md")
    assert record["results"]["rubric_count"] >= 1
