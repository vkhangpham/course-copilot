"""Default CodeAct registry wiring for the CourseGen PoC."""

from __future__ import annotations

from apps.codeact.registry import CodeActRegistry, ToolBinding
from apps.codeact.signatures import DraftLectureSection, EnforceCitations, PlanCourse
from apps.codeact.tools import (
    fetch_concepts,
    load_dataset_asset,
    lookup_paper,
    push_notebook_section,
    record_claim,
    run_sql_query,
    search_events,
)


def build_default_registry() -> CodeActRegistry:
    """Register placeholder tools/programs so the orchestrator can inspect them."""

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
    )
    registry.register_program(
        "DraftLectureSection",
        [
            "fetch_concepts",
            "search_events",
            "lookup_paper",
            "record_claim",
            "run_sql_query",
        ],
    )
    registry.register_program(
        "EnforceCitations",
        ["load_dataset_asset", "lookup_paper"],
    )

    return registry
