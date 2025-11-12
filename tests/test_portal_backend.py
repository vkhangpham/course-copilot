from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from apps.portal_backend.main import app, get_settings, PortalSettings


@pytest.fixture()
def portal_settings(tmp_path: Path) -> Iterator[PortalSettings]:
    outputs_dir = tmp_path / "outputs"
    artifacts_dir = outputs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    settings = PortalSettings(outputs_dir=outputs_dir, notebook_slug="database-systems-poc")
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield settings
    finally:
        app.dependency_overrides.pop(get_settings, None)


def _write_run(outputs_dir: Path, run_id: str = "20250101-000000") -> dict:
    artifacts_dir = outputs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    course_plan = outputs_dir / "course_plan.md"
    course_plan.write_text("# Course Plan\n\nWeek 1: Intro", encoding="utf-8")

    lectures_dir = outputs_dir / "lectures"
    lectures_dir.mkdir(parents=True, exist_ok=True)
    lecture_path = lectures_dir / "module_01.md"
    lecture_path.write_text("# Module 1\n\nContent", encoding="utf-8")

    eval_report = outputs_dir / "evaluations"
    eval_report.mkdir(parents=True, exist_ok=True)
    eval_report_path = eval_report / "run-eval.jsonl"
    eval_report_path.write_text('{"overall_score": 0.92}', encoding="utf-8")

    manifest = {
        "course_plan": str(course_plan),
        "lecture": str(lecture_path),
        "eval_report": str(eval_report_path),
        "provenance": str(outputs_dir / "provenance" / "run.jsonl"),
        "ablations": {"use_students": True, "use_world_model": True, "allow_recursion": True},
        "dataset_summary": {"concept_count": 30},
        "evaluation": {"overall_score": 0.92, "rubrics": [{"name": "Pedagogy", "passed": True}]},
        "world_model_highlights": {"concepts": [{"id": "relational_model", "summary": "Foundations"}]},
    }
    manifest_path = artifacts_dir / f"run-{run_id}-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_health_without_runs(portal_settings: PortalSettings) -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["latest_run_id"] is None


def test_list_runs_and_detail(portal_settings: PortalSettings) -> None:
    manifest = _write_run(portal_settings.outputs_dir)
    client = TestClient(app)

    runs_resp = client.get("/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) == 1
    run_id = runs[0]["run_id"]
    assert runs[0]["has_course_plan"] is True
    assert runs[0]["overall_score"] == pytest.approx(0.92)

    detail_resp = client.get(f"/runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["manifest"]["dataset_summary"] == manifest["dataset_summary"]
    assert "Course Plan" in detail["course_plan_excerpt"]
    assert detail["notebook_slug"] == "database-systems-poc"

    cp_resp = client.get(f"/runs/{run_id}/course-plan")
    assert cp_resp.status_code == 200
    assert cp_resp.text.startswith("# Course Plan")

    lecture_resp = client.get(f"/runs/{run_id}/lecture")
    assert lecture_resp.status_code == 200
    assert "Module 1" in lecture_resp.text
