"""Ensure we only use Pydantic v2-style validators/config."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pytest

TARGET_DIRS: tuple[str, ...] = ("apps", "ccopilot", "scripts", "tests", "world_model", "sandbox")
LEGACY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("legacy decorator", re.compile(r"@(?:root_)?validator\b")),
    ("legacy import", re.compile(r"\bfrom\s+pydantic\s+import\b[^\n]*\bvalidator\b")),
    ("legacy direct reference", re.compile(r"\bpydantic\.(?:root_)?validator\b")),
)


def _python_files(base_dirs: Iterable[Path]) -> Iterable[Path]:
    for directory in base_dirs:
        if not directory.exists():
            continue
        yield from directory.rglob("*.py")


def test_no_v1_pydantic_validators() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target_roots = [repo_root / directory for directory in TARGET_DIRS]
    this_file = Path(__file__).resolve()
    offenders: list[str] = []

    for path in _python_files(target_roots):
        if path == this_file:
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in LEGACY_PATTERNS:
            if pattern.search(text):
                relative_path = path.relative_to(repo_root)
                offenders.append(f"{relative_path} -> {label}")
                break

    if offenders:
        formatted = "\n".join(offenders)
        pytest.fail(f"Legacy Pydantic validator usage detected:\n{formatted}")
