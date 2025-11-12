"""
Typed configuration helpers for the CourseGen PoC pipeline.

These models intentionally live outside the yet-to-be-created `apps/` tree so
other agents can iterate on orchestration logic without waiting for repo
scaffolding to land. They will be imported by the eventual `run_poc` CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class CourseAudience(BaseModel):
    """High-level description of the intended learner."""

    persona: str = Field(..., description="Short label for the learner persona.")
    prior_knowledge: List[str] = Field(
        default_factory=list, description="List of prerequisite skills the learner is assumed to have."
    )
    goals: List[str] = Field(default_factory=list, description="Desired outcomes for the learner.")


class CourseConstraints(BaseModel):
    """Domain-specific levers that drive the plan + lecture generation."""

    model_config = ConfigDict()

    title: str
    description: Optional[str] = None
    duration_weeks: int = Field(..., ge=1, le=16)
    focus_areas: List[str] = Field(default_factory=list)
    tone: Literal["conversational", "formal", "technical", "mentor"] = "mentor"
    audience: CourseAudience
    required_sources: List[str] = Field(default_factory=list)
    banned_sources: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)

    @field_validator(
        "required_sources",
        "banned_sources",
        "focus_areas",
        "learning_objectives",
        mode="before",
    )
    @classmethod
    def strip_items(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        if isinstance(value, str):
            return value.strip()
        return value


class ModelConfig(BaseModel):
    """LLM/model defaults for teacher, TA, and student agents."""

    teacher_model: str = Field(default="gpt-4.1")
    ta_model: str = Field(default="gpt-4o-mini")
    student_model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=256)


class NotebookConfig(BaseModel):
    """Connection info for the Open Notebook instance."""

    api_base: str
    notebook_slug: str = Field(default="database-systems-poc")
    auth_token: Optional[str] = None


class WorldModelConfig(BaseModel):
    """Paths and settings for the symbolic world model store."""

    model_config = ConfigDict()

    schema_path: Path
    dataset_dir: Path
    sqlite_path: Path = Field(default=Path("world_model/world_model.sqlite"))

    @field_validator("schema_path", "dataset_dir", "sqlite_path", mode="before")
    @classmethod
    def coerce_path(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class EvaluationConfig(BaseModel):
    """Rubrics + quiz bank inputs used by student agents."""

    model_config = ConfigDict()

    rubrics_path: Path = Field(default=Path("evals/rubrics.yaml"))
    quiz_bank_path: Path = Field(default=Path("data/handcrafted/database_systems/quiz_bank.json"))
    max_mutations: int = Field(default=2, ge=0, le=5)

    @field_validator("rubrics_path", "quiz_bank_path", mode="before")
    @classmethod
    def coerce_path(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class PipelineConfig(BaseModel):
    """Top-level configuration for the orchestrator pipeline."""

    course: CourseConstraints
    models: ModelConfig = Field(default_factory=ModelConfig)
    notebook: NotebookConfig
    world_model: WorldModelConfig
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @model_validator(mode="before")
    @classmethod
    def ensure_sections_present(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        missing = [key for key in ("course", "notebook", "world_model") if key not in values]
        if missing:
            raise ValueError(f"Missing config sections: {', '.join(missing)}")
        return values


def read_yaml_file(path: Path) -> Dict[str, Any]:
    """Load a YAML file and return a dictionary."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {path}, received {type(data)}")
    return data


def load_course_constraints(path: Path) -> CourseConstraints:
    """Parse the course constraint YAML into a typed model."""
    data = read_yaml_file(path)
    try:
        return CourseConstraints.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid course constraints in {path}") from exc


def load_pipeline_config(path: Path) -> PipelineConfig:
    """Load the full pipeline config used by the run_poc CLI."""
    data = read_yaml_file(path)
    try:
        return PipelineConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid pipeline config in {path}") from exc


def merge_course_constraints(base: CourseConstraints, overrides: Dict[str, Any]) -> CourseConstraints:
    """
    Return a new CourseConstraints object by applying overrides on top of the base config.

    This is useful for ablations or quick experiments driven by CLI flags.
    """
    payload = base.model_dump()
    payload.update(overrides)
    try:
        return CourseConstraints.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Invalid overrides for CourseConstraints") from exc
