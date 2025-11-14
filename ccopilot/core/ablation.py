"""Helpers for toggling ablation modes in the CourseGen PoC."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel


class AblationSwitch(str, Enum):
    """Named toggles supported by the CLI."""

    NO_WORLD_MODEL = "no_world_model"
    NO_STUDENTS = "no_students"
    NO_RECURSION = "no_recursion"

    @classmethod
    def choices(cls) -> List[str]:
        return [member.value for member in cls]


class AblationConfig(BaseModel):
    """Representation of which subsystems are disabled for a run."""

    use_world_model: bool = True
    use_students: bool = True
    allow_recursion: bool = True

    def describe(self) -> str:
        enabled = []
        if self.use_world_model:
            enabled.append("world-model")
        if self.use_students:
            enabled.append("student-evals")
        if self.allow_recursion:
            enabled.append("recursion")
        return ", ".join(enabled) if enabled else "none"


def parse_ablation_flag(flag_value: str | None) -> AblationConfig:
    """
    Convert a comma-separated CLI flag into an AblationConfig.

    Examples
    --------
    - ``None`` or empty string → all subsystems enabled.
    - ``no_students`` → student agents disabled, everything else on.
    - ``no_world_model,no_recursion`` → disable world model + recursion.
    """
    config = AblationConfig()
    if not flag_value:
        return config

    tokens = [token.strip().lower() for token in flag_value.split(",") if token.strip()]
    for token in tokens:
        try:
            switch = AblationSwitch(token)
        except ValueError as exc:
            valid = ", ".join(AblationSwitch.choices())
            raise ValueError(f"Unknown ablation '{token}'. Valid options: {valid}") from exc

        if switch is AblationSwitch.NO_WORLD_MODEL:
            config.use_world_model = False
        elif switch is AblationSwitch.NO_STUDENTS:
            config.use_students = False
        elif switch is AblationSwitch.NO_RECURSION:
            config.allow_recursion = False

    return config
