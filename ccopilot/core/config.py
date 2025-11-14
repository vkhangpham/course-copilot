"""
Typed configuration helpers for the CourseGen PoC pipeline.

These models intentionally live outside the yet-to-be-created `apps/` tree so
other agents can iterate on orchestration logic without waiting for repo
scaffolding to land. They will be imported by the eventual `run_poc` CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

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
    prior_knowledge: List[str] = Field(default_factory=list, description="List of prerequisite skills the learner is assumed to have.")
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


class RoleModelConfig(BaseModel):
    """Provider-specific configuration for a single LM role."""

    model_config = ConfigDict(extra="allow")

    provider: Literal["openai"] = "openai"
    model: str
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=64)
    api_key_env: str | None = None
    api_base: str | None = None
    api_base_env: str | None = None

    @property
    def extra_kwargs(self) -> Dict[str, Any]:
        return getattr(self, "model_extra", {})


class ModelConfig(BaseModel):
    """LLM/model defaults for teacher, TA, and student agents."""

    model_config = ConfigDict(extra="ignore")

    teacher: RoleModelConfig = Field(default_factory=lambda: RoleModelConfig(model="gpt-5.1", reasoning={"effort": "high"}))
    ta: RoleModelConfig = Field(default_factory=lambda: RoleModelConfig(model="gpt-5-mini"))
    coder: RoleModelConfig = Field(default_factory=lambda: RoleModelConfig(model="gpt-5.1-codex-mini"))
    student: RoleModelConfig = Field(default_factory=lambda: RoleModelConfig(model="gpt-5-mini"))
    default_temperature: float = Field(default=1.0, ge=0.0, le=1.0)
    default_max_tokens: int = Field(default=32000, ge=256)

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_format(cls, data: Any) -> Any:
        if data is None or isinstance(data, ModelConfig):
            return data
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        # Flatten nested "models" blocks if present (e.g., config/model_config.yaml reference)
        models_block = payload.pop("models", None)
        if isinstance(models_block, dict):
            payload = {**payload, **models_block}

        # Normalize plural keys
        if "students" in payload and "student" not in payload:
            payload["student"] = payload.pop("students")
        if "teaching_assistants" in payload and "ta" not in payload:
            payload["ta"] = payload.pop("teaching_assistants")

        # Transform legacy flat fields
        if "teacher" not in payload and any(key in payload for key in ("teacher_model", "ta_model", "student_model")):
            teacher_model = payload.pop("teacher_model", None) or "gpt-5.1"
            ta_model = payload.pop("ta_model", None) or "gpt-5-mini"
            student_model = payload.pop("student_model", None) or ta_model or "gpt-5-mini"
            legacy_temp = payload.pop("temperature", None)
            legacy_tokens = payload.pop("max_tokens", None)
            payload.update(
                {
                    "teacher": {"provider": "openai", "model": teacher_model},
                    "ta": {"provider": "openai", "model": ta_model},
                    "student": {"provider": "openai", "model": student_model},
                }
            )
            if legacy_temp is not None:
                payload["default_temperature"] = legacy_temp
            if legacy_tokens is not None:
                payload["default_max_tokens"] = legacy_tokens

        payload.setdefault("teacher", {"provider": "openai", "model": "gpt-5.1", "reasoning": {"effort": "high"}})
        payload.setdefault("ta", {"provider": "openai", "model": "gpt-5-mini"})
        payload.setdefault("student", {"provider": "openai", "model": payload["ta"]["model"]})
        payload.setdefault("coder", {"provider": "openai", "model": "gpt-5.1-codex-mini"})

        return payload

    @property
    def teacher_model(self) -> str:
        return self.teacher.model

    @property
    def ta_model(self) -> str:
        return self.ta.model

    @property
    def student_model(self) -> str:
        return self.student.model

    @property
    def temperature(self) -> float:
        return self.default_temperature

    @property
    def max_tokens(self) -> int:
        return self.default_max_tokens

    def get_role(self, role: Literal["teacher", "ta", "student"]) -> RoleModelConfig:
        return getattr(self, role)


class NotebookConfig(BaseModel):
    """Connection info for the Open Notebook instance."""

    api_base: str
    notebook_slug: str = Field(default="database-systems-poc")
    auth_token: Optional[str] = None
    auto_create: bool = Field(default=True, description="Create notebook if missing before publishing")


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
    quiz_pass_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    rubric_pass_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    quiz_question_limit: int | None = Field(default=3, ge=1)
    generate_runtime_quiz: bool = Field(default=False)
    runtime_quiz_limit: int | None = Field(default=5, ge=1)

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


def _resolve_config_path(value: Any, base_dir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    else:
        path = path.resolve()
    return str(path)


def _absolutize_pipeline_paths(data: Dict[str, Any], base_dir: Path) -> None:
    world_model = data.get("world_model")
    if isinstance(world_model, dict):
        for key in ("schema_path", "dataset_dir", "sqlite_path"):
            if world_model.get(key):
                world_model[key] = _resolve_config_path(world_model[key], base_dir)

    evaluation = data.get("evaluation")
    if isinstance(evaluation, dict):
        for key in ("rubrics_path", "quiz_bank_path"):
            if evaluation.get(key):
                evaluation[key] = _resolve_config_path(evaluation[key], base_dir)


def load_course_constraints(path: Path) -> CourseConstraints:
    """Parse the course constraint YAML into a typed model."""
    data = read_yaml_file(path)
    try:
        return CourseConstraints.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid course constraints in {path}") from exc


def load_pipeline_config(path: Path, *, base_dir: Path | None = None) -> PipelineConfig:
    """Load the full pipeline config used by the run_poc CLI."""
    path = path.expanduser().resolve()
    data = read_yaml_file(path)
    _absolutize_pipeline_paths(data, base_dir=(base_dir or path.parent).resolve())
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
