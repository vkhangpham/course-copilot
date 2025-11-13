from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from scripts import validate_handcrafted

DATASET = Path(__file__).resolve().parents[1] / "data" / "handcrafted" / "database_systems"
runner = CliRunner()


def test_validate_handcrafted_cli_succeeds() -> None:
    result = runner.invoke(validate_handcrafted.app, [str(DATASET)])
    assert result.exit_code == 0
    assert "Dataset looks good" in result.stdout


def test_validate_handcrafted_cli_fail_on_warning(tmp_path: Path) -> None:
    dataset_copy = tmp_path / "dataset"
    shutil.copytree(DATASET, dataset_copy)
    quiz_path = dataset_copy / "quiz_bank.json"
    quizzes = json.loads(quiz_path.read_text(encoding="utf-8"))
    quizzes.append(
        {
            "id": "quiz-warning",
            "prompt": "Dummy prompt",
            "answer_sketch": "N/A",
            "learning_objectives": [],
            "reference_papers": ["missing-paper"],
        }
    )
    quiz_path.write_text(json.dumps(quizzes, indent=2), encoding="utf-8")

    result = runner.invoke(
        validate_handcrafted.app,
        [str(dataset_copy), "--fail-on-warning"],
    )

    assert result.exit_code == 1
    assert "quiz-warning" in result.stdout
    assert "unknown paper" in result.stdout.lower()
