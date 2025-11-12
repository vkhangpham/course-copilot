"""DSPy CodeAct signature definitions."""

from __future__ import annotations

import dspy


class PlanCourse(dspy.Signature):
    """Map structured course constraints into a multi-week outline."""

    constraints = dspy.InputField(
        desc="Serialized CourseConstraints payload (audience, tone, focus areas)."
    )
    outline = dspy.OutputField(
        desc="Markdown outline with modules, readings, and deliverables."
    )


class DraftLectureSection(dspy.Signature):
    """Expand a module plan plus grounded claims into a lecture section."""

    module = dspy.InputField(
        desc="Module metadata (week, learning objectives, required readings)."
    )
    claims = dspy.InputField(
        desc="List of grounded claims/observations fetched from the world model."
    )
    section = dspy.OutputField(
        desc="Markdown lecture or study-guide section with citations."
    )


class EnforceCitations(dspy.Signature):
    """Review markdown sections and inject/repair citation markup."""

    md_section = dspy.InputField(
        desc="Markdown output from a TA program (may have missing citations)."
    )
    corrected_section = dspy.OutputField(
        desc="Markdown with explicit citation tags suitable for Notebook export."
    )


__all__ = ["PlanCourse", "DraftLectureSection", "EnforceCitations"]
