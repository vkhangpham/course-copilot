"""Shared state adapters for the Database Systems symbolic world model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field


class WorldModelSnapshot(BaseModel):
    """Minimal snapshot metadata persisted alongside artifacts.

    This will expand once the world-model schema is finalized in ccopilot-o78.
    """

    concept_root: Path
    graph_store: Path
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class SharedStateHandles:
    """Thin wrapper so agents share the same storage contract."""

    concept_root: Path
    artifact_root: Path
    eval_root: Path

    def ensure_dirs(self) -> None:
        """Create directories up front so downstream agents can rely on them."""

        for directory in (self.concept_root, self.artifact_root, self.eval_root):
            directory.mkdir(parents=True, exist_ok=True)

    def snapshot_paths(self, label: str) -> WorldModelSnapshot:
        """Return deterministic output paths for a given run label."""

        graph_store = self.artifact_root / f"world_model_{label}.json"
        return WorldModelSnapshot(concept_root=self.concept_root, graph_store=graph_store)
