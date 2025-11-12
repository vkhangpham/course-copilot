"""Helpers for configuring DSPy language models from pipeline config."""

from __future__ import annotations

import os
from dataclasses import dataclass

import dspy

from ccopilot.core.config import ModelConfig


class DSPyConfigurationError(RuntimeError):
    """Raised when DSPy cannot be configured for the requested run."""


@dataclass(frozen=True, slots=True)
class DSPyModelHandles:
    """Concrete LM handles provisioned for each agent role."""

    teacher: object
    ta: object
    student: object


def _build_openai_lm(model_name: str, *, api_key: str, temperature: float, max_tokens: int) -> object:
    lm_cls = getattr(dspy, "OpenAI", None)
    kwargs = {
        "model": model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if lm_cls is not None:
        kwargs["api_key"] = api_key
    else:  # fallback to the generic LM wrapper (relies on env vars for auth)
        lm_cls = dspy.LM
    return lm_cls(**kwargs)


def configure_dspy_models(model_cfg: ModelConfig, *, api_key: str | None = None) -> DSPyModelHandles:
    """Instantiate DSPy OpenAI LMs for the teacher, TAs, and students."""

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise DSPyConfigurationError("OPENAI_API_KEY is required to configure DSPy")

    teacher = _build_openai_lm(
        model_cfg.teacher_model,
        api_key=key,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
    )
    ta = _build_openai_lm(
        model_cfg.ta_model,
        api_key=key,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
    )
    student = _build_openai_lm(
        model_cfg.student_model,
        api_key=key,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
    )

    dspy.settings.configure(lm=teacher)

    return DSPyModelHandles(teacher=teacher, ta=ta, student=student)


__all__ = [
    "DSPyConfigurationError",
    "DSPyModelHandles",
    "configure_dspy_models",
]
