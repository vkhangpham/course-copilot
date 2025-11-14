from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.ta_roles import DEFAULT_ROLES
from agents.teacher_rlm import TeacherRLM
from apps.orchestrator.notebook_publisher import NotebookSectionInput
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
        evaluation=EvaluationConfig(generate_runtime_quiz=False),
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
        dspy_handles=DSPyModelHandles(teacher=object(), ta=object(), coder=object(), student=object()),
    )


class RecordingTeacherRLM:
    def __init__(self) -> None:
        self._captured_actions: list[SimpleNamespace] = []
        self.action_log: list[SimpleNamespace] = []

    def record_action(self, action: str, role: str, payload: dict[str, object], result: dict[str, object]) -> None:
        entry = SimpleNamespace(action=action, role=role, payload=payload, result=result)
        self._captured_actions.append(entry)
        self.action_log.append(entry)


def _configure_eval_files(ctx: PipelineContext, tmp_path: Path) -> EvaluationConfig:
    rubrics_path = tmp_path / "rubrics.yaml"
    rubrics_path.parent.mkdir(parents=True, exist_ok=True)
    rubrics_yaml = "coverage:\n  description: Coverage\n  pass_threshold: 0.1\n  checklist:\n    - relational model\n    - transactions\n"
    rubrics_path.write_text(rubrics_yaml, encoding="utf-8")

    quiz_path = tmp_path / "quiz_bank.json"
    quiz_questions = [
        {
            "id": "quiz-coverage",
            "prompt": "Explain relational workloads",
            "answer_sketch": "relational sql transaction",
            "learning_objectives": ["coverage"],
            "difficulty": "easy",
        }
    ]
    quiz_path.write_text(json.dumps(quiz_questions), encoding="utf-8")

    eval_cfg = EvaluationConfig(
        rubrics_path=rubrics_path,
        quiz_bank_path=quiz_path,
        max_mutations=1,
        generate_runtime_quiz=False,
    )
    ctx.config = ctx.config.model_copy(update={"evaluation": eval_cfg})
    return eval_cfg


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
    assert registry.calls[0]["lm_handle"] is ctx.dspy_handles.coder


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
    assert draft_call["lm_handle"] is ctx.dspy_handles.coder
    assert enforce_call["lm_handle"] is ctx.dspy_handles.coder


def test_plan_fallback_records_stage_error(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)
    orch = TeacherOrchestrator(ctx)
    orch._offline_codeact = True  # force dataset fallback

    orch._emit_course_plan(ctx.paths.output_dir, dataset_summary, world_model_highlights={})

    assert orch.stage_errors
    last_error = orch.stage_errors[-1]
    assert last_error["stage"] == "codeact_fallback"
    assert last_error["context"]["program"] == "PlanCourse"


def test_lecture_fallback_records_stage_error(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    (ctx.paths.output_dir / "lectures").mkdir(parents=True, exist_ok=True)
    orch = TeacherOrchestrator(ctx)
    orch._offline_codeact = True  # force dataset fallback

    orch._emit_lecture(ctx.paths.output_dir / "lectures", dataset_summary, world_model_highlights={})

    assert orch.stage_errors
    last_error = orch.stage_errors[-1]
    assert last_error["stage"] == "codeact_fallback"
    assert last_error["context"]["program"] == "DraftLectureSection"


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


def test_teacher_hooks_expose_role_registry(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    orch.teacher_rlm = RecordingTeacherRLM()  # type: ignore[assignment]
    hooks = orch._build_teacher_hooks(world_model_highlights={})
    registry = hooks["list_ta_roles"]()
    assert isinstance(registry, list)
    assert {entry["name"] for entry in registry} == {role.name for role in DEFAULT_ROLES}
    sample = registry[0]
    assert set(sample["tools"]) == set(orch.ta_roles[sample["name"]].tool_whitelist)


def test_codeact_offline_mode_uses_fallbacks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    monkeypatch.setenv("COURSEGEN_CODEACT_OFFLINE", "1")
    ctx = _make_context(tmp_path)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)
    ctx.paths.output_dir.joinpath("lectures").mkdir(parents=True, exist_ok=True)
    orch = TeacherOrchestrator(ctx)
    highlights = {
        "syllabus_modules": [{"week": 1, "title": "Transactions", "outcomes": ["Explain ACID"]}],
        "concepts": [{"id": "tx", "name": "Transactions", "summary": "ACID foundations"}],
    }

    plan_path = orch._emit_course_plan(ctx.paths.output_dir, dataset_summary, highlights)
    plan_text = plan_path.read_text(encoding="utf-8")
    assert "CodeAct outline unavailable" in plan_text

    lecture_path = orch._emit_lecture(ctx.paths.output_dir / "lectures", dataset_summary, highlights)
    lecture_text = lecture_path.read_text(encoding="utf-8")
    assert "LectureAuthor TA output unavailable" in lecture_text


def test_request_ta_records_requester(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    orch.teacher_rlm = RecordingTeacherRLM()  # type: ignore[assignment]
    hooks = orch._build_teacher_hooks(world_model_highlights={})
    result = hooks["request_ta"]("SyllabusDesigner", requester="LectureAuthor", task={"week": 1})
    assert result.get("requested_by") == "LectureAuthor"
    assert any(
        action.action == "spawn_ta" and action.payload.get("requested_by") == "LectureAuthor"
        for action in orch.teacher_rlm._captured_actions  # type: ignore[attr-defined]
    )


def test_world_model_hooks_return_concepts(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    orch.teacher_rlm = TeacherRLM()

    class _StubTools:
        def query(self, concept_id: str) -> dict[str, str]:
            if concept_id != "relational_model":
                raise KeyError(concept_id)
            return {"id": concept_id, "name": "Relational Model"}

        def list_concepts(self, topic: str | None = None, limit: int | None = None) -> list[dict[str, str]]:
            rows = [
                {"id": "relational_model", "name": "Relational Model"},
                {"id": "transactions", "name": "Transactions"},
            ]
            return rows if limit is None else rows[:limit]

    orch._world_model_tools = _StubTools()  # type: ignore[attr-defined]
    hooks = orch._build_teacher_hooks(world_model_highlights={})

    result = hooks["wm_get"]("relational_model")
    assert result["status"] == "ok"
    assert result["concept"]["id"] == "relational_model"
    assert orch.teacher_rlm.action_log[-1].action == "wm_get"

    listing = hooks["wm_list"](topic="relational", limit=1)
    assert listing["status"] == "ok"
    assert len(listing["concepts"]) == 1
    assert orch.teacher_rlm.action_log[-1].action == "wm_list"


def test_world_model_hooks_handle_disabled_mode(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.ablations.use_world_model = False
    orch = TeacherOrchestrator(ctx)
    orch.teacher_rlm = TeacherRLM()
    hooks = orch._build_teacher_hooks(world_model_highlights={})

    fetch_result = hooks["wm_get"]("relational_model")
    list_result = hooks["wm_list"]()
    assert fetch_result["status"] == "disabled"
    assert list_result["status"] == "disabled"


def test_world_model_hook_tracks_runtime_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    orch.teacher_rlm = TeacherRLM()

    captured_paths: list[Path] = []

    class RecorderTools:
        def __init__(self, concept_root: Path, store_path: Path) -> None:
            captured_paths.append(Path(store_path).resolve())

        def query(self, concept_id: str) -> dict[str, str]:
            return {"id": concept_id, "name": concept_id}

        def list_concepts(self, topic: str | None = None, limit: int | None = None) -> list[dict[str, str]]:
            return [{"id": "relational_model", "name": "Relational Model"}]

    monkeypatch.setattr("apps.orchestrator.teacher.WorldModelTools", RecorderTools)

    store_a = (tmp_path / "store_a.sqlite").resolve()
    store_b = (tmp_path / "store_b.sqlite").resolve()

    orch._set_world_model_store_path(store_a)  # type: ignore[attr-defined]
    hooks = orch._build_teacher_hooks(world_model_highlights={})
    hooks["wm_get"]("relational_model")
    assert captured_paths[-1] == store_a

    orch._set_world_model_store_path(store_b)  # type: ignore[attr-defined]
    hooks["wm_get"]("relational_model")
    assert captured_paths[-1] == store_b


def test_build_teacher_tasks_covers_all_roles(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    tasks = orch._build_teacher_tasks(dataset_summary)
    assert {task.target for task in tasks} == {role.name for role in DEFAULT_ROLES}
    syllabus_task = next(task for task in tasks if task.target == "SyllabusDesigner")
    assert syllabus_task.payload["task"].get("dataset") == dataset_summary
    lecture_task = next(task for task in tasks if task.target == "LectureAuthor")
    assert lecture_task.payload["task"].get("module") == 1


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


def test_codeact_failure_records_stage_error(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    (ctx.paths.output_dir / "lectures").mkdir(parents=True, exist_ok=True)

    class ExplodingRegistry:
        def build_program(self, name: str, **_kwargs):
            if name not in {"DraftLectureSection", "EnforceCitations"}:
                raise KeyError(name)

            def runner(**_runner_kwargs):
                raise RuntimeError("boom")

            runner.invocations = []  # type: ignore[attr-defined]
            return runner

    registry = ExplodingRegistry()
    orch = TeacherOrchestrator(ctx, codeact_registry=registry)
    highlights = {
        "syllabus_modules": [{"week": 1, "title": "Foundations", "outcomes": ["Explain ACID"]}],
        "concepts": [{"id": "rel_model", "name": "Relational Model", "summary": "Foundations"}],
    }

    section = orch._generate_codeact_lecture_section(highlights, use_cache=False)
    assert section is None
    assert orch.stage_errors and orch.stage_errors[-1]["stage"] == "codeact_run"


def test_manifest_includes_stage_errors(tmp_path: Path, dataset_summary: dict[str, object]) -> None:
    ctx = _make_context(tmp_path)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)
    ctx.paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    ctx.paths.evaluations_dir.mkdir(parents=True, exist_ok=True)
    ctx.paths.logs_dir.mkdir(parents=True, exist_ok=True)
    course_plan = ctx.paths.output_dir / "course_plan.md"
    lecture = ctx.paths.output_dir / "lectures" / "module_01.md"
    lecture.parent.mkdir(parents=True, exist_ok=True)
    eval_report = ctx.paths.evaluations_dir / "run.jsonl"
    provenance = ctx.paths.logs_dir / "prov.jsonl"
    for path in (course_plan, lecture, eval_report, provenance):
        path.write_text("stub", encoding="utf-8")

    orch = TeacherOrchestrator(ctx)
    orch._record_stage_error("codeact_run", "boom")  # type: ignore[attr-defined]

    manifest_path = ctx.paths.artifacts_dir / "manifest.json"
    orch._emit_manifest(
        manifest_path,
        course_plan,
        lecture,
        eval_report,
        provenance,
        dataset_summary,
        ctx.config.world_model.sqlite_path,
        snapshot_exists=True,
        evaluation_payload={"status": "ok"},
        world_model_highlights={},
        highlight_artifact=None,
        teacher_trace=None,
        notebook_exports=None,
        notebook_export_summary=None,
        highlight_source="world_model",
    )

    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert doc["stage_errors"]


def test_stage_error_logged_when_rubrics_missing(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    eval_cfg = EvaluationConfig(
        rubrics_path=tmp_path / "missing_rubrics.yaml",
        quiz_bank_path=tmp_path / "quiz_bank.json",
        generate_runtime_quiz=False,
    )
    eval_cfg.quiz_bank_path.write_text("[]", encoding="utf-8")
    ctx.config = ctx.config.model_copy(update={"evaluation": eval_cfg})
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("Relational SQL", encoding="utf-8")

    orch = TeacherOrchestrator(ctx)
    result = orch._evaluate_artifacts(lecture_path, None)

    assert result["status"] == "missing_rubrics"
    assert orch.stage_errors and orch.stage_errors[-1]["stage"] == "student_eval"


def test_stage_error_logged_when_student_loop_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("COURSEGEN_DISABLE_LLM_STUDENTS", "1")
    ctx = _make_context(tmp_path)
    _configure_eval_files(ctx, tmp_path)
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("Relational SQL transactions", encoding="utf-8")

    def _boom(self, _path):  # noqa: D401
        raise RuntimeError("boom")

    monkeypatch.setattr("apps.orchestrator.teacher.StudentLoopRunner.run", _boom, raising=True)

    orch = TeacherOrchestrator(ctx)
    result = orch._evaluate_artifacts(lecture_path, None)

    assert result["status"] == "student_loop_error"
    assert orch.stage_errors[-1]["stage"] == "student_eval"


def test_stage_error_logged_on_non_passing_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("COURSEGEN_DISABLE_LLM_STUDENTS", "1")
    ctx = _make_context(tmp_path)
    _configure_eval_files(ctx, tmp_path)
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("Relational SQL transactions", encoding="utf-8")

    def _stub(self, _path):
        return {
            "use_students": True,
            "status": "max_mutations_reached",
            "attempts": [],
            "mutations": 2,
            "rubrics": {},
            "quiz": {},
        }

    monkeypatch.setattr("apps.orchestrator.teacher.StudentLoopRunner.run", _stub, raising=True)

    orch = TeacherOrchestrator(ctx)
    result = orch._evaluate_artifacts(lecture_path, None)

    assert result["status"] == "max_mutations_reached"
    assert orch.stage_errors[-1]["stage"] == "student_eval"


def test_student_llm_missing_raises_without_opt_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    _configure_eval_files(ctx, tmp_path)
    ctx.dspy_handles = DSPyModelHandles(teacher=object(), ta=object(), coder=object(), student=None)
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("Relational SQL", encoding="utf-8")
    monkeypatch.delenv("COURSEGEN_DISABLE_LLM_STUDENTS", raising=False)

    orch = TeacherOrchestrator(ctx)

    with pytest.raises(RuntimeError, match="Student LLM handle unavailable"):
        orch._evaluate_artifacts(lecture_path, None)


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


def test_publish_notebook_sections_reports_missing_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_context(tmp_path)
    orch = TeacherOrchestrator(ctx)
    ctx.paths.output_dir.mkdir(parents=True, exist_ok=True)
    lecture_dir = ctx.paths.output_dir / "lectures"
    lecture_dir.mkdir(parents=True, exist_ok=True)
    lecture_path = lecture_dir / "module.md"
    lecture_path.write_text("# Lecture\nBody", encoding="utf-8")
    missing_plan = ctx.paths.output_dir / "course_plan.md"

    class _StubPublisher:
        def __init__(self) -> None:
            self.calls: list[list[NotebookSectionInput]] = []

        def publish(self, sections: list[NotebookSectionInput]) -> list[dict[str, object]]:
            self.calls.append(list(sections))
            payloads: list[dict[str, object]] = []
            for idx, section in enumerate(sections, start=1):
                payloads.append(
                    {
                        "title": section.title,
                        "path": str(section.path) if section.path else None,
                        "response": {"status": "ok", "note_id": f"note-{idx}"},
                    }
                )
            return payloads

    stub_publisher = _StubPublisher()
    monkeypatch.setattr(TeacherOrchestrator, "_build_notebook_publisher", lambda self: stub_publisher)

    exports = orch._publish_notebook_sections(missing_plan, lecture_path)

    assert exports is not None
    assert stub_publisher.calls, "Expected lecture sections to be sent to NotebookPublisher"
    error_entries = [entry for entry in exports if entry.get("kind") == "section_error"]
    assert error_entries, "Missing error entry for the absent course plan"
    assert error_entries[0]["response"].get("reason") == "validation_failure"
    assert error_entries[0]["section"] == "course_plan"
    assert any(err["stage"] == "notebook_export" for err in orch.stage_errors)


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
