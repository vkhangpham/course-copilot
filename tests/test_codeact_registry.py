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
