from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.ta_roles import DEFAULT_ROLES
from apps.orchestrator.student_loop import MutationReason
from apps.orchestrator.teacher import TeacherOrchestrator
from ccopilot.core.ablation import AblationConfig
from ccopilot.core.config import (
    CourseConstraints,
    EvaluationConfig,
    ModelConfig,
    NotebookConfig,
    PipelineConfig,
    WorldModelConfig,
)
from ccopilot.core.dspy_runtime import DSPyModelHandles
from ccopilot.core.provenance import ProvenanceLogger
from ccopilot.pipeline.context import PipelineContext, PipelinePaths


class StubRegistry:
    def __init__(self, responses: dict[str, dict[str, str]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def build_program(self, name: str, *, allowed_tools=None, lm_handle=None, lm_role=None):
        if name not in self._responses:
            raise KeyError(name)
        self.calls.append(
            {
                "name": name,
                "allowed_tools": allowed_tools,
                "lm_handle": lm_handle,
                "lm_role": lm_role,
            }
        )
        response = self._responses[name]

        def runner(**kwargs):
            runner.invocations.append(kwargs)
            return SimpleNamespace(**response)

        runner.invocations = []  # type: ignore[attr-defined]
        return runner


def _make_context(tmp_path: Path) -> PipelineContext:
    config = PipelineConfig(
        course=CourseConstraints(
            title="Database Systems",
            description="",
            duration_weeks=4,
            focus_areas=["Transactions"],
            tone="mentor",
            audience={"persona": "Undergrad"},
            learning_objectives=["Explain ACID"],
        ),
        models=ModelConfig(),
        notebook=NotebookConfig(api_base="http://localhost:5055"),
        world_model=WorldModelConfig(
            schema_path=tmp_path / "schema.sql",
            dataset_dir=tmp_path / "dataset",
            sqlite_path=tmp_path / "world_model.sqlite",
        ),
        evaluation=EvaluationConfig(),
    )
    paths = PipelinePaths(
        repo_root=tmp_path,
        output_dir=tmp_path / "outputs",
        artifacts_dir=tmp_path / "outputs" / "artifacts",
        evaluations_dir=tmp_path / "outputs" / "evaluations",
        logs_dir=tmp_path / "outputs" / "logs",
    )
    provenance = ProvenanceLogger(tmp_path / "outputs" / "logs" / "prov.jsonl")
    return PipelineContext(
        config=config,
        ablations=AblationConfig(),
        paths=paths,
        env={},
        provenance=provenance,
        dspy_handles=DSPyModelHandles(teacher=object(), ta=object(), student=object()),
    )


@pytest.fixture()
def dataset_summary() -> dict[str, int | list[str]]:
    return {
        "concept_count": 30,
        "paper_count": 20,
        "timeline_count": 10,
        "quiz_count": 6,
        "top_domains": ["Transactions"],
    }


def test_emit_course_plan_includes_codeact_outline(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)
    registry = StubRegistry({"PlanCourse": {"outline": "### Week 1: Relational Thinking"}})
    orch = TeacherOrchestrator(ctx, codeact_registry=registry)

    plan_path = orch._emit_course_plan(ctx.paths.output_dir, dataset_summary, world_model_highlights={})
    contents = plan_path.read_text(encoding="utf-8")

    assert "AI-generated Outline (CodeAct)" in contents
    assert "Week 1: Relational Thinking" in contents
    syllabus_tools = next(role.tool_whitelist for role in DEFAULT_ROLES if role.name == "SyllabusDesigner")
    assert registry.calls and registry.calls[0]["allowed_tools"] == syllabus_tools
    assert registry.calls[0]["lm_handle"] is ctx.dspy_handles.ta


def test_emit_lecture_prefers_codeact_section(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    (ctx.paths.output_dir / "lectures").mkdir(parents=True, exist_ok=True)
    registry = StubRegistry(
        {
            "PlanCourse": {"outline": "Placeholder"},
            "DraftLectureSection": {"section": "## TA Draft Section\nContent"},
            "EnforceCitations": {"corrected_section": "## Clean Section\nContent + citations"},
        }
    )
    orch = TeacherOrchestrator(ctx, codeact_registry=registry)
    highlights = {
        "syllabus_modules": [{"week": 1, "title": "Relational Model", "outcomes": ["ACID basics"]}],
        "concepts": [{"id": "rel_model", "name": "Relational Model", "summary": "Foundations"}],
    }

    lecture_path = orch._emit_lecture(ctx.paths.output_dir / "lectures", dataset_summary, highlights)
    text = lecture_path.read_text(encoding="utf-8")
    assert "Clean Section" in text
    lecture_tools = next(role.tool_whitelist for role in DEFAULT_ROLES if role.name == "LectureAuthor")
    draft_call = next(call for call in registry.calls if call["name"] == "DraftLectureSection")
    enforce_call = next(call for call in registry.calls if call["name"] == "EnforceCitations")
    assert draft_call["allowed_tools"] == lecture_tools
    assert enforce_call["allowed_tools"] == lecture_tools
    assert draft_call["lm_handle"] is ctx.dspy_handles.ta
    assert enforce_call["lm_handle"] is ctx.dspy_handles.ta


def test_recursion_ablation_still_runs_codeact(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=True, use_students=True, allow_recursion=False)
    registry = StubRegistry({"PlanCourse": {"outline": "Week 1"}})
    orch = TeacherOrchestrator(ctx, codeact_registry=registry)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)

    orch._emit_course_plan(ctx.paths.output_dir, dataset_summary, world_model_highlights={})

    assert registry.calls, "CodeAct programs should still run when recursion is disabled"


def test_recursion_ablation_keeps_notebook_exports_enabled(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=True, use_students=True, allow_recursion=False)
    orch = TeacherOrchestrator(ctx)
    assert orch._notebook_exports_enabled() is True


def test_mutation_loop_requests_fresh_lecture_sections(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    lecture_path = tmp_path / "outputs" / "lectures" / "module_01.md"
    lecture_path.parent.mkdir(parents=True, exist_ok=True)
    lecture_path.write_text("## Seed Lecture\nOriginal body", encoding="utf-8")

    orch = TeacherOrchestrator(ctx, codeact_registry=object())
    world_model_highlights = {
        "syllabus_modules": [{"week": 1, "title": "Foundations", "outcomes": ["Explain ACID"]}],
        "concepts": [{"id": "rel_model", "name": "Relational Model", "summary": "Foundations"}],
    }

    call_log: list[str] = []

    def fake_run_program(name: str, **kwargs):  # type: ignore[override]
        if name == "DraftLectureSection":
            iteration = str(len(call_log) + 1)
            call_log.append(iteration)
            return SimpleNamespace(section=f"## Draft {iteration}\ncontent {iteration}")
        if name == "EnforceCitations":
            return SimpleNamespace(corrected_section=kwargs.get("md_section"))
        return SimpleNamespace()

    orch._run_codeact_program = fake_run_program  # type: ignore[method-assign]

    first = orch._generate_codeact_lecture_section(world_model_highlights)
    assert first and "Draft 1" in first
    assert call_log == ["1"]

    reason = MutationReason(
        failing_rubrics=["coverage"],
        failing_questions=["q1"],
        overall_score=0.5,
        quiz_pass_rate=0.4,
    )
    orch._apply_mutation(lecture_path, iteration=1, reason=reason, world_model_highlights=world_model_highlights)

    mutated_text = lecture_path.read_text(encoding="utf-8")
    assert "Draft 2" in mutated_text
    assert call_log == ["1", "2"], "Mutation loop should bypass cached lecture sections"


def test_world_model_highlights_source_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)

    def fake_dataset_highlights(self):  # type: ignore[override]
        return {"syllabus_modules": [{"week": 1, "title": "Fallback", "outcomes": []}]}

    monkeypatch.setattr(TeacherOrchestrator, "_collect_dataset_highlights", fake_dataset_highlights)

    store_path = tmp_path / "world_model.sqlite"
    store_path.write_text("", encoding="utf-8")

    def boom(**_kwargs):
        raise RuntimeError("wm down")

    monkeypatch.setattr("apps.orchestrator.teacher.fetch_concepts", boom)

    highlights, source = orch._collect_world_model_highlights(store_path)
    assert source == "dataset"
    assert highlights.get("syllabus_modules")


def test_world_model_highlights_empty_dataset_fallback_marks_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)

    monkeypatch.setattr(TeacherOrchestrator, "_collect_dataset_highlights", lambda self: {})

    store_path = tmp_path / "world_model.sqlite"
    if store_path.exists():
        store_path.unlink()

    highlights, source = orch._collect_world_model_highlights(store_path)
    assert highlights == {}
    assert source == "dataset"


def test_notebook_placeholder_reason_explains_missing_slug(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=False, use_students=False, allow_recursion=False)
    notebook_cfg = ctx.config.notebook.model_copy(update={"notebook_slug": ""})
    ctx.config = ctx.config.model_copy(update={"notebook": notebook_cfg})

    orch = TeacherOrchestrator(ctx)
    assert orch._notebook_exports_enabled() is False
    assert orch._notebook_skip_reason() == "missing_notebook_slug"

    artifacts = orch.run_coursegen(
        dataset_summary=dataset_summary,
        world_model_store=tmp_path / "store.sqlite",
        snapshot_exists=False,
    )

    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    exports = manifest.get("notebook_exports") or []
    assert exports, "Expected placeholder notebook export"
    assert exports[0]["response"].get("reason") == "missing_notebook_slug"


def test_world_model_highlights_source_reports_world_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)

    monkeypatch.setattr(TeacherOrchestrator, "_collect_dataset_highlights", lambda self: {})

    store_path = tmp_path / "world_model.sqlite"
    store_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "apps.orchestrator.teacher.fetch_concepts",
        lambda **_kwargs: [{"id": "c1", "name": "Concept", "summary": "Summary", "children": [], "prerequisites": []}],
    )
    monkeypatch.setattr(
        "apps.orchestrator.teacher.search_events",
        lambda **_kwargs: [{"year": 2024, "event": "Milestone", "summary": "Context", "citation_id": "paper-1"}],
    )
    monkeypatch.setattr(
        "apps.orchestrator.teacher.lookup_paper",
        lambda _paper_id, **_kwargs: {"id": "paper-1", "title": "Paper", "year": 2024, "venue": "Conf"},
    )

    highlights, source = orch._collect_world_model_highlights(store_path)
    assert source == "world_model"
    assert "concepts" in highlights


def test_no_world_model_ablation_marks_dataset_source_without_highlights(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dataset_summary: dict[str, object]
) -> None:
    ctx = _make_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=False, use_students=False, allow_recursion=False)
    ctx.config = ctx.config.model_copy(update={"notebook": None})

    class _Stub:
        pass

    orch = TeacherOrchestrator(ctx, teacher_rlm=_Stub())

    monkeypatch.setattr(TeacherOrchestrator, "_collect_dataset_highlights", lambda self: {})

    artifacts = orch.run_coursegen(
        dataset_summary=dataset_summary,
        world_model_store=tmp_path / "store.sqlite",
        snapshot_exists=False,
    )

    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest.get("highlight_source") == "dataset"
    assert artifacts.highlight_source == "dataset"
