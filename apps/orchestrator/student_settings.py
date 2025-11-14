"""Shared helpers for toggling student LLM behavior."""

from __future__ import annotations

import os

DISABLE_LLM_ENV = "COURSEGEN_DISABLE_LLM_STUDENTS"


def students_llm_disabled() -> bool:
    """Return True when student LLM graders should be disabled."""

    value = os.getenv(DISABLE_LLM_ENV)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
