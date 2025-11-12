"""Default CodeAct registry wiring for the CourseGen PoC."""

from __future__ import annotations

from ccopilot.core.dspy_runtime import DSPyModelHandles

from apps.codeact.programs import (
    build_draft_lecture_program,
    build_enforce_citations_program,
    build_plan_course_program,
)
from apps.codeact.registry import CodeActRegistry, ToolBinding
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


def build_default_registry(
    *,
    dspy_handles: DSPyModelHandles | None = None,
) -> CodeActRegistry:
    """Register CodeAct tools/programs for the orchestrator."""

    teacher_lm = dspy_handles.teacher if dspy_handles else None
    ta_lm = dspy_handles.ta if dspy_handles else None
    student_lm = dspy_handles.student if dspy_handles else None

    registry = CodeActRegistry()
    registry.register_tool(
        ToolBinding(
            name="fetch_concepts",
            signature="topic -> concept[]",
            handler=fetch_concepts,
            description="Query the world-model store for concepts and their relationships.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="record_claim",
            signature="subject, claim -> claim_id",
            handler=record_claim,
            description="Store a grounded claim linked to a concept.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="list_claims",
            signature="subject? -> claim[]",
            handler=list_claims,
            description="List recorded claims, optionally filtered by subject.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="list_relationships",
            signature="filters -> relationship[]",
            handler=list_relationships,
            description="Inspect concept relationships (prereqs, hierarchies).",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="run_sql_query",
            signature="sql -> rows",
            handler=run_sql_query,
            description="Execute read-only DuckDB queries for analytics/examples.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="load_dataset_asset",
            signature="path -> object",
            handler=load_dataset_asset,
            description="Read YAML/JSON assets from the handcrafted dataset bundle.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="search_events",
            signature="query -> timeline[]",
            handler=search_events,
            description="Search the world-model timeline for events related to a concept or keyword.",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="lookup_paper",
            signature="paper_id -> paper",
            handler=lookup_paper,
            description="Fetch citation metadata for a paper id (authors, venue, year).",
        )
    )
    registry.register_tool(
        ToolBinding(
            name="push_notebook_section",
            signature="title, md -> notebook_section",
            handler=push_notebook_section,
            description="Send markdown sections to the Open Notebook API (placeholder).",
        )
    )

    registry.register_program(
        "PlanCourse",
        ["fetch_concepts", "load_dataset_asset", "search_events", "lookup_paper", "run_sql_query"],
        factory=lambda lm=teacher_lm: build_plan_course_program(lm=lm),
    )
    registry.register_program(
        "DraftLectureSection",
        [
            "fetch_concepts",
            "search_events",
            "lookup_paper",
            "record_claim",
            "list_relationships",
            "list_claims",
            "run_sql_query",
            "push_notebook_section",
        ],
        factory=lambda lm=ta_lm: build_draft_lecture_program(lm=lm),
    )
    registry.register_program(
        "EnforceCitations",
        ["load_dataset_asset", "lookup_paper"],
        factory=lambda lm=student_lm or ta_lm or teacher_lm: build_enforce_citations_program(lm=lm),
    )

    return registry
