from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.orchestrator.pipeline import Orchestrator
from ccopilot.core.ablation import AblationConfig
from ccopilot.core.config import (
    CourseAudience,
    CourseConstraints,
    EvaluationConfig,
    ModelConfig,
    NotebookConfig,
    PipelineConfig,
    WorldModelConfig,
)
from ccopilot.core.provenance import ProvenanceLogger
from ccopilot.pipeline.context import PipelineContext, PipelinePaths


def _make_stub_context(tmp_path: Path) -> PipelineContext:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    config = PipelineConfig(
        course=CourseConstraints(
            title="Databases",
            description="",
            duration_weeks=4,
            focus_areas=["Transactions"],
            tone="mentor",
            audience=CourseAudience(persona="Undergrad", prior_knowledge=[], goals=[]),
            learning_objectives=["Explain ACID"],
        ),
        models=ModelConfig(),
        notebook=NotebookConfig(api_base="https://notebook.test"),
        world_model=WorldModelConfig(
            schema_path=tmp_path / "schema.sql",
            dataset_dir=dataset_dir,
            sqlite_path=tmp_path / "world_model.sqlite",
        ),
        evaluation=EvaluationConfig(
            rubrics_path=tmp_path / "rubrics.yaml",
            quiz_bank_path=tmp_path / "quiz_bank.json",
        ),
    )
    output_dir = tmp_path / "outputs"
    paths = PipelinePaths(
        repo_root=tmp_path,
        output_dir=output_dir,
        artifacts_dir=output_dir / "artifacts",
        evaluations_dir=output_dir / "evaluations",
        logs_dir=output_dir / "logs",
    )
    provenance = ProvenanceLogger(paths.logs_dir / "provenance.jsonl")
    return PipelineContext(
        config=config,
        ablations=AblationConfig(),
        paths=paths,
        env={},
        provenance=provenance,
    )


def _dataset_summary() -> dict[str, object]:
    return {
        "concept_count": 0,
        "paper_count": 0,
        "timeline_count": 0,
        "quiz_count": 0,
        "top_domains": [],
    }


def test_stub_orchestrator_marks_dataset_highlight_source_when_world_model_disabled(tmp_path: Path) -> None:
    ctx = _make_stub_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=False, use_students=False, allow_recursion=False)
    orchestrator = Orchestrator(ctx)

    artifacts = orchestrator.run(
        dataset_summary=_dataset_summary(),
        world_model_store=ctx.config.world_model.sqlite_path,
        snapshot_exists=False,
    )

    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert artifacts.highlight_source == "dataset"
    assert manifest["highlight_source"] == "dataset"
    exports = manifest.get("notebook_exports")
    assert isinstance(exports, list) and exports
    assert exports[0]["response"]["reason"] == "notebook_stubbed"
    summary = manifest.get("notebook_export_summary")
    assert summary["skipped"] == 1


def test_stub_orchestrator_marks_dataset_source_when_world_model_store_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _make_stub_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=True, use_students=False, allow_recursion=False)
    orchestrator = Orchestrator(ctx)
    store_path = ctx.config.world_model.sqlite_path
    if store_path.exists():
        store_path.unlink()

    monkeypatch.setattr(Orchestrator, "_collect_dataset_highlights", lambda self: {})

    artifacts = orchestrator.run(
        dataset_summary=_dataset_summary(),
        world_model_store=store_path,
        snapshot_exists=False,
    )

    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert artifacts.highlight_source == "dataset"
    assert manifest["highlight_source"] == "dataset"


def test_stub_orchestrator_marks_world_model_highlight_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = _make_stub_context(tmp_path)
    ctx.ablations = AblationConfig(use_world_model=True, use_students=False, allow_recursion=False)
    orchestrator = Orchestrator(ctx)
    store_path = ctx.config.world_model.sqlite_path
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "apps.orchestrator.pipeline.fetch_concepts",
        lambda **_: [
            {
                "id": "concept-1",
                "name": "Concept",
                "summary": "Summary",
                "children": [],
                "prerequisites": [],
            }
        ],
    )
    monkeypatch.setattr("apps.orchestrator.pipeline.search_events", lambda **_: [])
    monkeypatch.setattr(
        "apps.orchestrator.pipeline.lookup_paper",
        lambda *_args, **_kwargs: {"id": "paper-1", "title": "Paper", "year": 2024},
    )

    artifacts = orchestrator.run(
        dataset_summary=_dataset_summary(),
        world_model_store=store_path,
        snapshot_exists=True,
    )
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest["highlight_source"] == "world_model"
    assert artifacts.highlight_source == "world_model"
    assert artifacts.notebook_exports and artifacts.notebook_export_summary
