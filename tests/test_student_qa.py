import json
from pathlib import Path

import pytest

from apps.orchestrator.student_qa import StudentQuizEvaluator


def _write_quiz(tmp_path: Path) -> Path:
    quiz_path = tmp_path / "quiz.json"
    quiz = [
        {
            "id": "quiz-redo",
            "prompt": "Explain redo logging",
            "answer_sketch": "Redo logs track history and must be replayed",
            "learning_objectives": ["recovery"],
            "difficulty": "medium",
        }
    ]
    quiz_path.write_text(json.dumps(quiz), encoding="utf-8")
    return quiz_path


def test_quiz_evaluator_respects_word_boundaries(tmp_path: Path) -> None:
    quiz_path = _write_quiz(tmp_path)
    evaluator = StudentQuizEvaluator(quiz_path, pass_threshold=0.5, question_limit=None)

    lecture = tmp_path / "lecture.md"
    lecture.write_text("This incredible demo says nothing about logging internals.", encoding="utf-8")
    result = evaluator.evaluate_path(lecture).as_dict()
    record = result["questions"][0]
    assert record["matched_keywords"] == []
    assert record["score"] == 0.0
    assert record["passed"] is False

    lecture.write_text(
        "Redo logs track history and must be replayed to ensure durability.",
        encoding="utf-8",
    )
    result = evaluator.evaluate_path(lecture).as_dict()
    record = result["questions"][0]
    assert set(record["matched_keywords"]) >= {"redo", "logs"}
    assert record["score"] > 0.0
    assert record["passed"] is True


def test_quiz_evaluator_accepts_runtime_questions(tmp_path: Path) -> None:
    questions = [
        {
            "id": "runtime-1",
            "prompt": "Describe redo logging",
            "answer_sketch": "Redo logging replays persisted changes",
            "learning_objectives": ["recovery"],
        }
    ]
    evaluator = StudentQuizEvaluator(questions=questions, pass_threshold=0.5)
    lecture = tmp_path / "lecture.md"
    lecture.write_text("Redo logging replays persisted changes for durability.", encoding="utf-8")
    result = evaluator.evaluate_path(lecture).as_dict()
    record = result["questions"][0]
    assert record["passed"] is True
    assert record["matched_keywords"]


def test_quiz_evaluator_requires_input() -> None:
    with pytest.raises(ValueError):
        StudentQuizEvaluator()
