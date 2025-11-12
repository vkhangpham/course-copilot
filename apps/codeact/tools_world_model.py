"""Placeholder world-model CRUD tools for the CodeAct sandbox."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


class WorldModelTools:
    def __init__(self, concept_root: Path):
        self.concept_root = concept_root

    def query(self, concept_id: str) -> Dict[str, str]:  # pragma: no cover - placeholder
        raise NotImplementedError("World model querying will ship with ccopilot-o78 data.")

    def list_concepts(self) -> List[Dict[str, str]]:  # pragma: no cover
        raise NotImplementedError
