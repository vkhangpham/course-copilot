"""Backwards-compatible exports for older docs/tests."""

from __future__ import annotations

from apps.codeact.programs import (
    build_draft_lecture_program,
    build_enforce_citations_program,
    build_plan_course_program,
)

__all__ = [
    "build_plan_course_program",
    "build_draft_lecture_program",
    "build_enforce_citations_program",
]
