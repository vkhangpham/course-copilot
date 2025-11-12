"""Student/Grader scaffolding for the self-evolving loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class GradingBackend(Protocol):
    def grade(self, rubric: dict, submission: str) -> dict:
        ...


@dataclass
class StudentGraderConfig:
    name: str
    rubric_path: str
    passing_threshold: float


class StudentLoop:
    """Placeholder for the rubric-driven grading/mutation loop."""

    def __init__(self, backend: GradingBackend) -> None:
        self.backend = backend

    def evaluate(self, grader: StudentGraderConfig, submission: str) -> dict:
        rubric = {"path": grader.rubric_path}
        return self.backend.grade(rubric, submission)
