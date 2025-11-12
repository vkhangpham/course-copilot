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
        tool_whitelist=["fetch_concepts", "run_sql_query"],
        prompt_path="prompts/ta_syllabus.txt",
    ),
    TARoleSpec(
        name="LectureAuthor",
        mandate="Draft fully cited lecture sections for a specific module.",
        tool_whitelist=["fetch_concepts", "record_claim", "push_notebook_section"],
        prompt_path="prompts/ta_lecture.txt",
    ),
]
