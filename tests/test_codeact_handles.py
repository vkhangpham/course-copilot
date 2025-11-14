from types import SimpleNamespace
from unittest import mock

from apps.orchestrator.codeact_registry import build_default_registry


@mock.patch("apps.orchestrator.codeact_registry.build_enforce_citations_program")
@mock.patch("apps.orchestrator.codeact_registry.build_draft_lecture_program")
@mock.patch("apps.orchestrator.codeact_registry.build_plan_course_program")
def test_registry_passes_ta_handle(mock_plan, mock_lecture, mock_enforce) -> None:
    mock_plan.return_value = mock.Mock(name="PlanCourseProgram")
    mock_lecture.return_value = mock.Mock(name="DraftLectureProgram")
    mock_enforce.return_value = mock.Mock(name="EnforceProgram")
    handles = SimpleNamespace(ta=object())

    registry = build_default_registry(dspy_handles=handles)
    registry.build_program("PlanCourse")
    registry.build_program("DraftLectureSection")
    registry.build_program("EnforceCitations")

    assert mock_plan.call_args.kwargs.get("lm") is handles.ta
    assert mock_lecture.call_args.kwargs.get("lm") is handles.ta
    assert mock_enforce.call_args.kwargs.get("lm") is handles.ta
