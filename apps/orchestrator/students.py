"""Simulated student/graders scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class StudentRubric:
    """Represents a machine-readable rubric definition."""

    name: str
    prompt_path: Path
    weight: float = 1.0


class StudentGraderPool:
    """Placeholder for the future self-evolving agent loop."""

    def __init__(self, rubrics: List[StudentRubric]):
        self.rubrics = rubrics

    def evaluate(self, artifact_path: Path) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError(
            "Grader pool will be implemented once rubrics land in ccopilot-o78."
        )
