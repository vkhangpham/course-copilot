"""Helpers for configuring DSPy language models from pipeline config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import dspy

from ccopilot.core.config import ModelConfig, RoleModelConfig


class DSPyConfigurationError(RuntimeError):
    """Raised when DSPy cannot be configured for the requested run."""


@dataclass(frozen=True, slots=True)
class DSPyModelHandles:
    """Concrete LM handles provisioned for each agent role."""

    teacher: object
    ta: object
    coder: object | None = None
    student: object


def _build_openai_lm(
    model_name: str,
    *,
    api_key: str,
    temperature: float,
    max_tokens: int,
    api_base: str | None = None,
    extra_kwargs: Dict[str, Any] | None = None,
) -> object:
    lm_cls = getattr(dspy, "OpenAI", None)
    kwargs = {
        "model": model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    if lm_cls is not None:
        kwargs["api_key"] = api_key
    else:  # fallback to the generic LM wrapper (relies on env vars for auth)
        lm_cls = dspy.LM
    return lm_cls(**kwargs)


def _resolve_api_key(role_cfg: RoleModelConfig, role_name: str) -> str | None:
    preferred_envs = []
    if role_cfg.api_key_env:
        preferred_envs.append(role_cfg.api_key_env)
    preferred_envs.append(f"OPENAI_API_KEY_{role_name.upper()}")
    preferred_envs.append("OPENAI_API_KEY")
    for env_var in preferred_envs:
        if env_var and (value := os.getenv(env_var)):
            return value
    return None


def _resolve_api_base(role_cfg: RoleModelConfig, role_name: str) -> str | None:
    if role_cfg.api_base:
        return role_cfg.api_base
    env_candidates = []
    if role_cfg.api_base_env:
        env_candidates.append(role_cfg.api_base_env)
    env_candidates.append(f"OPENAI_API_BASE_{role_name.upper()}")
    env_candidates.append("OPENAI_API_BASE")
    for env_var in env_candidates:
        if env_var and (value := os.getenv(env_var)):
            return value
    return None


def _build_model_for_role(
    role_cfg: RoleModelConfig,
    role_name: str,
    model_cfg: ModelConfig,
    override_key: str | None,
) -> object:
    if role_cfg.provider != "openai":
        raise DSPyConfigurationError(f"Unsupported provider '{role_cfg.provider}' for role '{role_name}'")

    api_key = override_key or _resolve_api_key(role_cfg, role_name)
    if not api_key:
        expected_env = role_cfg.api_key_env or f"OPENAI_API_KEY_{role_name.upper()}"
        raise DSPyConfigurationError(f"Missing API key for {role_name} models; set {expected_env} or OPENAI_API_KEY.")

    api_base = _resolve_api_base(role_cfg, role_name)
    temperature = role_cfg.temperature if role_cfg.temperature is not None else model_cfg.default_temperature
    max_tokens = role_cfg.max_tokens if role_cfg.max_tokens is not None else model_cfg.default_max_tokens

    return _build_openai_lm(
        role_cfg.model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        api_base=api_base,
        extra_kwargs=role_cfg.extra_kwargs,
    )


def configure_dspy_models(model_cfg: ModelConfig, *, api_key: str | None = None) -> DSPyModelHandles:
    """Instantiate DSPy OpenAI LMs for the teacher, TA dialog, coder CodeAct runs, and students."""

    teacher = _build_model_for_role(model_cfg.teacher, "teacher", model_cfg, api_key)
    ta = _build_model_for_role(model_cfg.ta, "ta", model_cfg, api_key)
    coder = _build_model_for_role(model_cfg.coder, "coder", model_cfg, api_key)
    student = _build_model_for_role(model_cfg.student, "student", model_cfg, api_key)

    dspy.settings.configure(lm=teacher)

    return DSPyModelHandles(teacher=teacher, ta=ta, coder=coder, student=student)


__all__ = [
    "DSPyConfigurationError",
    "DSPyModelHandles",
    "configure_dspy_models",
]
