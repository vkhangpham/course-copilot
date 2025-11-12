from pathlib import Path

from apps.orchestrator.ta_roles.exercise_author import ExerciseAuthor

DATASET_ROOT = Path("data/handcrafted/database_systems")


def test_exercise_author_from_dataset() -> None:
    author = ExerciseAuthor(DATASET_ROOT)
    exercises = author.draft(limit=2)

    assert exercises, "Expected exercises based on quiz bank"
    assert exercises[0].description
    assert exercises[0].expected_outcome


def test_exercise_author_filters_topics(tmp_path: Path) -> None:
    quiz_bank = [
        {
            "id": "quiz-a",
            "prompt": "Describe transactions",
            "learning_objectives": ["transactions"],
            "difficulty": "easy",
        },
        {
            "id": "quiz-b",
            "prompt": "Explain storage",
            "learning_objectives": ["storage"],
            "difficulty": "medium",
        },
    ]
    (tmp_path / "quiz_bank.json").write_text(__import__("json").dumps(quiz_bank), encoding="utf-8")
    concepts = {
        "concepts": {
            "transactions": {"summary": "ACID guarantees"},
            "storage": {"summary": "Physical layout"},
        }
    }
    (tmp_path / "concepts.yaml").write_text(__import__("yaml").safe_dump(concepts), encoding="utf-8")

    author = ExerciseAuthor(tmp_path)
    exercises = author.draft(topics=["storage"], limit=5)

    assert len(exercises) == 1
    assert "physical" in exercises[0].expected_outcome.lower()
