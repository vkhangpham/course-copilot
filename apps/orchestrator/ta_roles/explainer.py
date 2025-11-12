"""TA role for writing explanations and worked examples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ExplanationChunk:
    heading: str
    body_md: str
    citations: List[str]


class Explainer:
    def write(self, module: str) -> List[ExplanationChunk]:  # pragma: no cover
        raise NotImplementedError("Explainer logic will be handled post-scaffolding.")
