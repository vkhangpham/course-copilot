"""Entry points for constructing DSPy CodeAct programs."""

from __future__ import annotations

import dspy

from apps.codeact.signatures import DraftLectureSection, EnforceCitations, PlanCourse
from apps.codeact.tools import (
    fetch_concepts,
    load_dataset_asset,
    push_notebook_section,
    record_claim,
    run_sql_query,
)


def build_plan_course_program() -> dspy.Module:
    """Return a PlanCourse CodeAct program wired with safe tools."""

    program = dspy.CodeAct(
        PlanCourse,
        tools=[fetch_concepts, load_dataset_asset, run_sql_query],
        max_iters=5,
    )
    return program


def build_draft_lecture_program() -> dspy.Module:
    program = dspy.CodeAct(
        DraftLectureSection,
        tools=[fetch_concepts, record_claim, push_notebook_section],
        max_iters=6,
    )
    return program


def build_enforce_citations_program() -> dspy.Module:
    program = dspy.CodeAct(
        EnforceCitations,
        tools=[load_dataset_asset],
        max_iters=3,
    )
    return program
