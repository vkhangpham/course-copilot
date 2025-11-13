from types import SimpleNamespace
from unittest import mock

import pytest

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

    mock_plan.assert_called_once_with(tools=mock.ANY, lm=None)
    mock_lecture.assert_called_once_with(tools=mock.ANY, lm=None)
    mock_enforce.assert_called_once_with(tools=mock.ANY, lm=None)


def test_registry_applies_allowed_tools() -> None:
    registry = build_default_registry()
    program = registry.build_program("PlanCourse", allowed_tools=["fetch_concepts", "run_sql_query"])
    assert program is not None


def test_registry_rejects_missing_allowed_tools() -> None:
    registry = build_default_registry()
    with pytest.raises(ValueError):
        registry.build_program("PlanCourse", allowed_tools=["unknown_tool"])


@mock.patch("apps.orchestrator.codeact_registry.build_plan_course_program")
def test_registry_forwards_lm_handle(mock_plan: mock.MagicMock) -> None:
    mock_plan.return_value = object()
    registry = build_default_registry()
    registry.build_program("PlanCourse", lm_handle="custom_lm")
    mock_plan.assert_called_with(tools=mock.ANY, lm="custom_lm")


@mock.patch("apps.orchestrator.codeact_registry.build_plan_course_program")
def test_registry_resolves_lm_role(mock_plan: mock.MagicMock) -> None:
    mock_plan.return_value = object()
    handles = SimpleNamespace(teacher=object(), ta=object(), student=object())
    registry = build_default_registry(dspy_handles=handles)
    registry.build_program("PlanCourse", lm_role="teacher")
    mock_plan.assert_called_with(tools=mock.ANY, lm=handles.teacher)


@mock.patch("apps.orchestrator.codeact_registry.build_draft_lecture_program")
def test_registry_uses_default_role_when_not_provided(mock_program: mock.MagicMock) -> None:
    mock_program.return_value = object()
    handles = SimpleNamespace(teacher=object(), ta=object(), student=object())
    registry = build_default_registry(dspy_handles=handles)
    registry.build_program("DraftLectureSection")
    mock_program.assert_called_with(tools=mock.ANY, lm=handles.ta)
