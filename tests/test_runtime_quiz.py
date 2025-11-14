from pathlib import Path

import pytest

from apps.orchestrator.runtime_quiz import generate_quiz_questions
from ccopilot.core.validation import ValidationFailure


def test_generate_quiz_questions_from_concepts(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    concepts = dataset / "concepts.yaml"
    concepts.write_text(
        """
concepts:
  relational_model:
    name: Relational Model
    summary: Relations, tuples, and integrity constraints.
  transactions:
    name: Transactions
    summary: Guarantees for concurrent updates.
        """.strip()
    )

    questions = generate_quiz_questions(dataset, limit=1)
    assert len(questions) == 1
    assert questions[0].id == "runtime-relational_model"
    assert "Relational Model" in questions[0].prompt
    assert "Relations" in questions[0].answer_sketch


def test_generate_quiz_questions_requires_concepts(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    with pytest.raises(ValidationFailure):
        generate_quiz_questions(dataset)
