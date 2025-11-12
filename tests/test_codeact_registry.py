from unittest import mock

import pytest
from types import SimpleNamespace

from apps.codeact.registry import CodeActRegistry, ToolBinding
from apps.orchestrator.codeact_registry import build_default_registry


def test_registry_describes_world_model_tools() -> None:
    registry = build_default_registry()
    description = registry.describe()
    assert "fetch_concepts" in description["tools"]
    assert "search_events" in description["tools"]
    assert "lookup_paper" in description["tools"]


def test_programs_include_lookup_and_events() -> None:
    registry = build_default_registry()
    programs = registry.describe()["programs"]
    assert "PlanCourse" in programs
    plan_tools = programs["PlanCourse"]
    assert "search_events" in plan_tools
    assert "lookup_paper" in plan_tools
    draft_tools = programs["DraftLectureSection"]
    assert "lookup_paper" in draft_tools
    assert "push_notebook_section" in draft_tools


def test_build_program_without_factory_raises() -> None:
    registry = CodeActRegistry()
    registry.register_tool(
        ToolBinding(
            name="noop",
            signature="noop",
            handler=lambda: "noop",
            description="test tool",
        )
    )
    registry.register_program("TestProgram", ["noop"])
    with pytest.raises(KeyError):
        registry.build_program("TestProgram")


@mock.patch("apps.orchestrator.codeact_registry.build_plan_course_program")
@mock.patch("apps.orchestrator.codeact_registry.build_draft_lecture_program")
@mock.patch("apps.orchestrator.codeact_registry.build_enforce_citations_program")
def test_default_registry_builds_programs(
    mock_enforce: mock.MagicMock,
    mock_lecture: mock.MagicMock,
    mock_plan: mock.MagicMock,
) -> None:
    mock_plan.return_value = object()
    mock_lecture.return_value = object()
    mock_enforce.return_value = object()

    registry = build_default_registry()

    assert registry.build_program("PlanCourse") is mock_plan.return_value
    assert registry.build_program("DraftLectureSection") is mock_lecture.return_value
    assert registry.build_program("EnforceCitations") is mock_enforce.return_value

    mock_plan.assert_called_once()
    mock_lecture.assert_called_once()
    mock_enforce.assert_called_once()


@mock.patch("apps.orchestrator.codeact_registry.build_plan_course_program")
@mock.patch("apps.orchestrator.codeact_registry.build_draft_lecture_program")
@mock.patch("apps.orchestrator.codeact_registry.build_enforce_citations_program")
def test_registry_passes_lm_handles(
    mock_enforce: mock.MagicMock,
    mock_lecture: mock.MagicMock,
    mock_plan: mock.MagicMock,
) -> None:
    handles = SimpleNamespace(teacher=object(), ta=object(), student=object())

    registry = build_default_registry(dspy_handles=handles)
    registry.build_program("PlanCourse")
    registry.build_program("DraftLectureSection")
    registry.build_program("EnforceCitations")

    mock_plan.assert_called_with()
    mock_lecture.assert_called_with()
    mock_enforce.assert_called_with()
