"""Factory helpers for DSPy CodeAct programs."""

from __future__ import annotations

import dspy

from apps.codeact.signatures import DraftLectureSection, EnforceCitations, PlanCourse
from apps.codeact.tools import (
    fetch_concepts,
    list_claims,
    list_relationships,
    load_dataset_asset,
    lookup_paper,
    push_notebook_section,
    record_claim,
    run_sql_query,
    search_events,
)

DEFAULT_PLAN_ITERS = 5
DEFAULT_LECTURE_ITERS = 6
DEFAULT_ENFORCE_ITERS = 3


def build_plan_course_program(
    *,
    max_iters: int = DEFAULT_PLAN_ITERS,
) -> dspy.Module:
    """Return a PlanCourse CodeAct program wired with safe tools."""

    kwargs: dict[str, object] = {
        "tools": [fetch_concepts, load_dataset_asset, search_events, lookup_paper, run_sql_query],
        "max_iters": max_iters,
    }
    return dspy.CodeAct(PlanCourse, **kwargs)


def build_draft_lecture_program(
    *,
    max_iters: int = DEFAULT_LECTURE_ITERS,
) -> dspy.Module:
    """Return a DraftLectureSection CodeAct program."""

    kwargs: dict[str, object] = {
        "tools": [
            fetch_concepts,
            search_events,
            lookup_paper,
            record_claim,
            list_relationships,
            list_claims,
            run_sql_query,
            push_notebook_section,
        ],
        "max_iters": max_iters,
    }
    return dspy.CodeAct(DraftLectureSection, **kwargs)


def build_enforce_citations_program(
    *,
    max_iters: int = DEFAULT_ENFORCE_ITERS,
) -> dspy.Module:
    """Return an EnforceCitations CodeAct program."""

    kwargs: dict[str, object] = {
        "tools": [load_dataset_asset, lookup_paper],
        "max_iters": max_iters,
    }
    return dspy.CodeAct(EnforceCitations, **kwargs)


__all__ = [
    "build_plan_course_program",
    "build_draft_lecture_program",
    "build_enforce_citations_program",
]
