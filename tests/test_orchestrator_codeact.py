from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.orchestrator.pipeline import Orchestrator
from ccopilot.core.ablation import AblationConfig
from ccopilot.core.config import CourseConstraints, ModelConfig, NotebookConfig, PipelineConfig, WorldModelConfig, EvaluationConfig
from ccopilot.core.provenance import ProvenanceLogger
from ccopilot.pipeline.context import PipelineContext, PipelinePaths


class StubRegistry:
    def __init__(self, responses: dict[str, dict[str, str]]) -> None:
        self._responses = responses

    def build_program(self, name: str):
        if name not in self._responses:
            raise KeyError(name)

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
    orch = Orchestrator(ctx, codeact_registry=registry)

    plan_path = orch._emit_course_plan(ctx.paths.output_dir, dataset_summary, world_model_highlights={})
    contents = plan_path.read_text(encoding="utf-8")

    assert "AI-generated Outline (CodeAct)" in contents
    assert "Week 1: Relational Thinking" in contents


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
    orch = Orchestrator(ctx, codeact_registry=registry)
    highlights = {
        "syllabus_modules": [{"week": 1, "title": "Relational Model", "outcomes": ["ACID basics"]}],
        "concepts": [{"id": "rel_model", "name": "Relational Model", "summary": "Foundations"}],
    }

    lecture_path = orch._emit_placeholder_lecture(ctx.paths.output_dir / "lectures", dataset_summary, highlights)
    text = lecture_path.read_text(encoding="utf-8")
    assert "Clean Section" in text
