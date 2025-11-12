"""Declarative DSPy signatures used by CodeAct programs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Signature:
    name: str
    description: str
    inputs: Dict[str, str]
    output: str


PlanCourse = Signature(
    name="PlanCourse",
    description="constraints -> outline",
    inputs={"constraints": "Serialized CourseConstraints"},
    output="markdown outline",
)

DraftLectureSection = Signature(
    name="DraftLectureSection",
    description="module context -> markdown section",
    inputs={"module": "Module metadata", "claims": "List[Claim]"},
    output="markdown section",
)

EnforceCitations = Signature(
    name="EnforceCitations",
    description="md_section -> md_section",
    inputs={"md_section": "Markdown"},
    output="markdown section",
)

__all__ = ["Signature", "PlanCourse", "DraftLectureSection", "EnforceCitations"]
