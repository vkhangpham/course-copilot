"""Role definition for the syllabus designer TA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class WeeklyModule:
    week: int
    title: str
    outcomes: List[str]
    readings: List[str]


class SyllabusDesigner:
    """Placeholder agent. Real logic added in ccopilot-syy."""

    def propose_modules(self, concept_root: Path) -> List[WeeklyModule]:  # pragma: no cover
        raise NotImplementedError("Syllabus generation pending dataset creation.")
