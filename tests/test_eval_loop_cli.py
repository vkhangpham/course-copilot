from pathlib import Path

from typer.testing import CliRunner

from apps.orchestrator.eval_loop import app


runner = CliRunner()


def _seed_artifacts(base: Path) -> tuple[Path, Path, Path]:
    artifacts = base / "outputs"
    lectures = artifacts / "lectures"
    evaluations = artifacts / "evaluations"
    lectures.mkdir(parents=True)
    evaluations.mkdir(parents=True)

    lecture_path = lectures / "module.md"
    lecture_path.write_text(
        "# Module\n\nThe relational model underpins transactions and recovery logs.",
        encoding="utf-8",
    )

    rubric_path = base / "rubric.yaml"
    rubric_path.write_text(
        """
coverage:
  description: "simple"
  pass_threshold: 0.0
  checklist:
    - "mentions relational"
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    return artifacts, lectures, rubric_path


def test_eval_loop_quiet_flag(tmp_path):
    artifacts_dir, lectures_dir, rubric = _seed_artifacts(tmp_path)

    result = runner.invoke(
        app,
        [
            "--artifacts-dir",
            str(artifacts_dir),
            "--lectures-dir",
            str(lectures_dir.relative_to(artifacts_dir)),
            "--rubric",
            str(rubric),
        ],
    )
    assert result.exit_code == 0
    assert "Evaluated 1 artifact" in result.stdout

    quiet_result = runner.invoke(
        app,
        [
            "--artifacts-dir",
            str(artifacts_dir),
            "--lectures-dir",
            str(lectures_dir.relative_to(artifacts_dir)),
            "--rubric",
            str(rubric),
            "--quiet",
        ],
    )
    assert quiet_result.exit_code == 0
    assert quiet_result.stdout.strip() == ""
