"""Default CodeAct registry wiring for the CourseGen PoC."""

from __future__ import annotations

from apps.codeact.programs import (
    build_draft_lecture_program,
    build_enforce_citations_program,
    build_plan_course_program,
)
from apps.codeact.registry import CodeActRegistry, ToolBinding
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


def build_default_registry(*, dspy_handles=None) -> CodeActRegistry:
    """Register CodeAct tools/programs for the orchestrator."""

    registry = CodeActRegistry(dspy_handles=dspy_handles)
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
            name="link_concepts",
            signature="source, target, relation -> relationship",
            handler=link_concepts,
            description="Create or reinforce edges between concept nodes.",
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
            name="append_timeline_event",
            signature="event -> timeline_event",
            handler=append_timeline_event,
            description="Append a grounded milestone to the observations table.",
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
    registry.register_tool(
        ToolBinding(
            name="persist_outline",
            signature="outline -> artifact",
            handler=persist_outline,
            description="Store course outline artifacts in the world-model for reuse.",
        )
    )

    registry.register_program(
        "PlanCourse",
        ["fetch_concepts", "load_dataset_asset", "search_events", "lookup_paper", "run_sql_query", "persist_outline"],
        factory=lambda tools=None, lm=None: build_plan_course_program(
            tools=tools,
            lm=lm,
        ),
        default_lm_role="ta",
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
            "link_concepts",
            "append_timeline_event",
            "persist_outline",
            "push_notebook_section",
        ],
        factory=lambda tools=None, lm=None: build_draft_lecture_program(
            tools=tools,
            lm=lm,
        ),
        default_lm_role="ta",
    )
    registry.register_program(
        "EnforceCitations",
        ["load_dataset_asset", "lookup_paper"],
        factory=lambda tools=None, lm=None: build_enforce_citations_program(
            tools=tools,
            lm=lm,
        ),
        default_lm_role="ta",
    )

    return registry
