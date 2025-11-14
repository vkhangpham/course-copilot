"""Shared helpers for locating the handcrafted dataset."""

from __future__ import annotations

import os
from pathlib import Path

ENV_REPO_ROOT = "COURSEGEN_REPO_ROOT"
ENV_DATASET_DIR = "COURSEGEN_DATASET_DIR"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATASET_SUBPATH = Path("data/handcrafted/database_systems")


def resolve_dataset_root(dataset_root: Path | None = None, *, repo_root: Path | None = None) -> Path:
    """Resolve the dataset root, honoring env overrides."""

    if dataset_root is not None:
        return Path(dataset_root).expanduser().resolve()

    dataset_env = os.environ.get(ENV_DATASET_DIR)
    if dataset_env:
        return Path(dataset_env).expanduser().resolve()

    repo_override = os.environ.get(ENV_REPO_ROOT)
    if repo_override:
        base_root = Path(repo_override).expanduser().resolve()
    else:
        base_root = Path(repo_root).expanduser().resolve() if repo_root is not None else _REPO_ROOT
    return (base_root / _DATASET_SUBPATH).resolve()
