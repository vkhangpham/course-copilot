"""TA role for curating readings and citations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class ReadingRecommendation:
    identifier: str
    title: str
    why_it_matters: str
    citation: str


class ReadingCurator:
    def curate(self, concept_root: Path) -> List[ReadingRecommendation]:  # pragma: no cover
        raise NotImplementedError("Reading curator will use world model data soon.")
