"""TA role for synthesizing database systems history/timeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TimelineEvent:
    year: int
    event: str
    impact: str


class TimelineSynthesizer:
    def build(self, timeline_file: Path) -> List[TimelineEvent]:  # pragma: no cover
        raise NotImplementedError("Timeline synthesis will land with ccopilot-o78 data.")
