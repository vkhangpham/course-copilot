"""TA role specifications used by the Teacher orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TARoleSpec:
    """Describe the instructions and allowed tools for a TA role."""

    name: str
    mandate: str
    tool_whitelist: Sequence[str]
    prompt_path: str


DEFAULT_ROLES = [
    TARoleSpec(
        name="SyllabusDesigner",
        mandate="Transform constraints into a coherent multi-week course outline.",
        tool_whitelist=[
            "fetch_concepts",
            "load_dataset_asset",
            "search_events",
            "lookup_paper",
            "run_sql_query",
            "persist_outline",
        ],
        prompt_path="prompts/ta_syllabus.txt",
    ),
    TARoleSpec(
        name="LectureAuthor",
        mandate="Draft fully cited lecture sections for a specific module.",
        tool_whitelist=[
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
        prompt_path="prompts/ta_lecture.txt",
    ),
]
