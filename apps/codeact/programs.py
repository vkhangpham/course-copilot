"""Factory helpers for DSPy CodeAct programs."""

from __future__ import annotations

from typing import Sequence

import dspy

from apps.codeact.signatures import DraftLectureSection, EnforceCitations, PlanCourse
from apps.codeact.tools import (
    append_timeline_event,
    fetch_concepts,
    link_concepts,
    list_claims,
    list_relationships,
    load_dataset_asset,
    lookup_paper,
    persist_outline,
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
    tools: Sequence | None = None,
    lm: object | None = None,
) -> dspy.Module:
    """Return a PlanCourse CodeAct program wired with safe tools."""

    toolset = (
        list(tools)
        if tools is not None
        else [
            fetch_concepts,
            load_dataset_asset,
            search_events,
            lookup_paper,
            run_sql_query,
            persist_outline,
        ]
    )
    program = dspy.CodeAct(
        PlanCourse,
        tools=toolset,
        max_iters=max_iters,
    )
    return _wrap_with_lm(program, lm)


def build_draft_lecture_program(
    *,
    max_iters: int = DEFAULT_LECTURE_ITERS,
    tools: Sequence | None = None,
    lm: object | None = None,
) -> dspy.Module:
    """Return a DraftLectureSection CodeAct program."""

    toolset = (
        list(tools)
        if tools is not None
        else [
            fetch_concepts,
            search_events,
            lookup_paper,
            record_claim,
            list_relationships,
            list_claims,
            run_sql_query,
            link_concepts,
            append_timeline_event,
            persist_outline,
            push_notebook_section,
        ]
    )
    program = dspy.CodeAct(
        DraftLectureSection,
        tools=toolset,
        max_iters=max_iters,
    )
    return _wrap_with_lm(program, lm)


def build_enforce_citations_program(
    *,
    max_iters: int = DEFAULT_ENFORCE_ITERS,
    tools: Sequence | None = None,
    lm: object | None = None,
) -> dspy.Module:
    """Return an EnforceCitations CodeAct program."""

    toolset = list(tools) if tools is not None else [load_dataset_asset, lookup_paper]
    program = dspy.CodeAct(
        EnforceCitations,
        tools=toolset,
        max_iters=max_iters,
    )
    return _wrap_with_lm(program, lm)


def _wrap_with_lm(program: dspy.Module, lm_handle: object | None) -> dspy.Module:
    if lm_handle is None:
        return program
    return _LMScopedProgram(program, lm_handle)


class _LMScopedProgram:
    """Wrapper that temporarily swaps DSPy's active LM before execution."""

    def __init__(self, program: dspy.Module, lm_handle: object) -> None:
        self._program = program
        self._lm = lm_handle

    def __call__(self, *args, **kwargs):
        try:
            previous = object.__getattribute__(dspy.settings, "lm")
            had_attr = True
        except AttributeError:
            previous = None
            had_attr = False

        dspy.settings.configure(lm=self._lm)
        try:
            return self._program(*args, **kwargs)
        finally:
            if had_attr:
                dspy.settings.configure(lm=previous)
            else:
                dspy.settings.configure(lm=None)


__all__ = [
    "build_plan_course_program",
    "build_draft_lecture_program",
    "build_enforce_citations_program",
]
