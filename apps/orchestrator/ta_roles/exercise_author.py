"""TA role for writing exercises/projects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Exercise:
    title: str
    description: str
    expected_outcome: str
    difficulty: str = "medium"


class ExerciseAuthor:
    def draft(self, modules: List[str]) -> List[Exercise]:  # pragma: no cover
        raise NotImplementedError("Exercise authoring requires module context.")
