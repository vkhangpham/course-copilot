from unittest import mock

from apps.codeact import programs
from apps.codeact.signatures import DraftLectureSection, EnforceCitations, PlanCourse
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


@mock.patch("apps.codeact.programs.dspy")
def test_plan_course_program_uses_expected_tools(mock_dspy) -> None:
    program = programs.build_plan_course_program(max_iters=7)
    assert program is mock_dspy.CodeAct.return_value

    args, kwargs = mock_dspy.CodeAct.call_args
    assert args[0] is PlanCourse
    assert kwargs["max_iters"] == 7
    tool_names = [tool.__name__ for tool in kwargs["tools"]]
    assert tool_names == [
        fetch_concepts.__name__,
        load_dataset_asset.__name__,
        search_events.__name__,
        lookup_paper.__name__,
        run_sql_query.__name__,
    ]


@mock.patch("apps.codeact.programs.dspy")
def test_draft_lecture_program_wires_all_tools(mock_dspy) -> None:
    programs.build_draft_lecture_program(max_iters=4)
    args, kwargs = mock_dspy.CodeAct.call_args
    assert args[0] is DraftLectureSection
    tool_names = {tool.__name__ for tool in kwargs["tools"]}
    assert {
        fetch_concepts.__name__,
        search_events.__name__,
        lookup_paper.__name__,
        record_claim.__name__,
        list_relationships.__name__,
        list_claims.__name__,
        run_sql_query.__name__,
        push_notebook_section.__name__,
    } == tool_names
    assert kwargs["max_iters"] == 4


@mock.patch("apps.codeact.programs.dspy")
def test_enforce_citations_program(mock_dspy) -> None:
    programs.build_enforce_citations_program(max_iters=2)
    args, kwargs = mock_dspy.CodeAct.call_args
    assert args[0] is EnforceCitations
    assert kwargs["max_iters"] == 2
    tool_names = [tool.__name__ for tool in kwargs["tools"]]
    assert tool_names == [load_dataset_asset.__name__, lookup_paper.__name__]
