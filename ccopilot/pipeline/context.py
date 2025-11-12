"""Shared context objects for the CourseGen pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ccopilot.core.ablation import AblationConfig
from ccopilot.core.config import PipelineConfig
from ccopilot.core.provenance import ProvenanceLogger


class PipelinePaths(BaseModel):
    """Canonical directories used during a pipeline run."""

    repo_root: Path
    output_dir: Path
    artifacts_dir: Path
    evaluations_dir: Path
    logs_dir: Path

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("repo_root", "output_dir", "artifacts_dir", "evaluations_dir", "logs_dir", mode="before")
    @classmethod
    def _expand(cls, value: Path | str) -> Path:
        return Path(value).expanduser().resolve()

    def ensure_directories(self) -> None:
        """Create directories if they do not yet exist."""
        for path in (
            self.output_dir,
            self.artifacts_dir,
            self.evaluations_dir,
            self.logs_dir,
            self.lectures_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def lectures_dir(self) -> Path:
        return self.output_dir / "lectures"


class PipelineContext(BaseModel):
    """Aggregated runtime context for orchestrator execution."""

    config: PipelineConfig
    ablations: AblationConfig
    paths: PipelinePaths
    env: Dict[str, str] = Field(default_factory=dict)
    provenance: ProvenanceLogger

    model_config = ConfigDict(arbitrary_types_allowed=True)
