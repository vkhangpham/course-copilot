from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from fastapi import HTTPException

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


def _write_run(
    outputs_dir: Path,
    run_id: str = "20250101-000000",
    *,
    include_notebook: bool = False,
    notebook_slug: str = "database-systems-poc",
) -> dict:
    artifacts_dir = outputs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    course_plan = outputs_dir / "course_plan.md"
    course_plan.write_text("# Course Plan\n\nWeek 1: Intro", encoding="utf-8")

    lectures_dir = outputs_dir / "lectures"
    lectures_dir.mkdir(parents=True, exist_ok=True)
    lecture_path = lectures_dir / "module_01.md"
    lecture_path.write_text("# Module 1\n\nContent", encoding="utf-8")

    eval_dir = outputs_dir / "evaluations"
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_report_path = eval_dir / "run-eval.jsonl"
    eval_report_path.write_text('{"overall_score": 0.92, "rubrics": [{"name": "Pedagogy", "passed": true}]}', encoding="utf-8")

    provenance_dir = outputs_dir / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    provenance_path = provenance_dir / f"run-{run_id}.jsonl"
    provenance_path.write_text("{\"stage\": \"test\"}", encoding="utf-8")

    trace_dir = outputs_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / f"run-{run_id}-trace.jsonl"
    trace_path.write_text("trace-line", encoding="utf-8")

    logs_dir = outputs_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    teacher_trace_path = logs_dir / f"teacher-trace-{run_id}.json"
    teacher_trace_path.write_text(
        json.dumps(
            {
                "summary": "Simulated teacher loop",
                "prompt": "prompts/teacher_seed.txt",
                "actions": [
                    {"action": "plan", "target": "SyllabusDesigner", "payload": {"week": 1}, "result": "ok"}
                ],
            }
        ),
        encoding="utf-8",
    )

    notebook_exports = None
    if include_notebook:
        notebook_exports = [
            {
                "kind": "preflight",
                "title": "notebook_preflight",
                "response": {"status": "skipped", "reason": "auto_create_disabled"},
            },
            {
                "title": "Course Plan",
                "path": str(course_plan),
                "citations": ["codd-1970"],
                "response": {"status": "ok", "notebook": notebook_slug, "id": "note-1"},
            },
        ]
        notebook_summary = {
            "total": 1,
            "success": 1,
            "skipped": 0,
            "errors": 0,
            "note_ids": ["note-1"],
            "queued_exports": [],
        }
    else:
        notebook_summary = None

    manifest = {
        "course_plan": str(course_plan),
        "lecture": str(lecture_path),
        "eval_report": str(eval_report_path),
        "provenance": str(provenance_path),
        "ablations": {"use_students": True, "use_world_model": True, "allow_recursion": True},
        "dataset_summary": {"concept_count": 30},
        "evaluation": {
            "overall_score": 0.92,
            "rubrics": [{"name": "Pedagogy", "passed": True}],
            "attempts": [
                {
                    "iteration": 1,
                    "rubrics": {"overall_score": 0.5, "rubrics": []},
                    "quiz": {"pass_rate": 0.5, "questions": []},
                    "triggered_mutation": {"failing_rubrics": ["coverage"], "failing_questions": []},
                }
            ],
        },
        "world_model_highlights": {"concepts": [{"id": "relational_model", "summary": "Foundations"}]},
        "world_model_highlight_artifact": str(artifacts_dir / f"run-{run_id}-highlights.json"),
        "teacher_trace": str(teacher_trace_path),
    }
    if notebook_exports is not None:
        manifest["notebook_exports"] = notebook_exports
        manifest["notebook_export_summary"] = notebook_summary
    (artifacts_dir / f"run-{run_id}-highlights.json").write_text("{}", encoding="utf-8")
    manifest_path = artifacts_dir / f"run-{run_id}-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _first_actual_export(manifest: dict) -> dict:
    exports = manifest.get("notebook_exports") or []
    for entry in exports:
        if str(entry.get("kind", "")).lower() == "preflight":
            continue
        return entry
    raise AssertionError("No actual notebook export found")


def test_health_without_runs(portal_settings: PortalSettings) -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["latest_run_id"] is None


def test_list_runs_and_detail(portal_settings: PortalSettings) -> None:
    manifest = _write_run(portal_settings.outputs_dir, include_notebook=True)
    client = TestClient(app)

    runs_resp = client.get("/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) == 1
    run_id = runs[0]["run_id"]
    assert runs[0]["has_course_plan"] is True
    assert runs[0]["overall_score"] == pytest.approx(0.92)
    assert runs[0]["notebook_export_summary"]["success"] == 1

    detail_resp = client.get(f"/runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["manifest"]["dataset_summary"] == manifest["dataset_summary"]
    assert "Course Plan" in detail["course_plan_excerpt"]
    assert detail["notebook_slug"] == "database-systems-poc"
    first_export = detail["notebook_exports"][0]
    assert first_export["status"] == "ok"
    assert first_export["note_id"] == "note-1"
    assert all(entry["title"] != "notebook_preflight" for entry in detail["notebook_exports"])
    assert detail["evaluation_attempts"][0]["iteration"] == 1
    assert detail["evaluation_attempts"][0]["overall_score"] == 0.5
    assert any(trace["name"] == "provenance" for trace in detail["trace_files"])

    teacher_meta = detail["teacher_trace"]
    assert teacher_meta["action_count"] == 1
    assert teacher_meta["summary"] == "Simulated teacher loop"

    attempts = detail["evaluation_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["iteration"] == 1
    assert attempts[0]["quiz_pass_rate"] == pytest.approx(0.5)
    assert attempts[0]["failing_rubrics"] == ["coverage"]

    trace_names = {trace["name"] for trace in detail["trace_files"]}
    assert "teacher_trace" in trace_names

    assert detail["manifest"].get("notebook_exports") is not None

    trace_resp = client.get(f"/runs/{run_id}/traces/teacher_trace")
    assert trace_resp.status_code == 200
    assert "Simulated teacher loop" in trace_resp.text

    notebook_resp = client.get(f"/runs/{run_id}/notebook-exports")
    assert notebook_resp.status_code == 200
    notebook_entries = notebook_resp.json()
    assert notebook_entries
    assert notebook_entries[0]["note_id"] == "note-1"
    assert all(entry["title"] != "notebook_preflight" for entry in notebook_entries)

    cp_resp = client.get(f"/runs/{run_id}/course-plan")
    assert cp_resp.status_code == 200
    assert cp_resp.text.startswith("# Course Plan")

    lecture_resp = client.get(f"/runs/{run_id}/lecture")
    assert lecture_resp.status_code == 200
    assert "Module 1" in lecture_resp.text


def test_run_detail_handles_missing_artifacts(portal_settings: PortalSettings) -> None:
    manifest = _write_run(portal_settings.outputs_dir, include_notebook=True)
    course_plan_path = Path(manifest["course_plan"])
    course_plan_path.unlink()

    client = TestClient(app)
    response = client.get("/runs/20250101-000000")
    assert response.status_code == 200
    data = response.json()
    assert data["course_plan_excerpt"] is None


def test_latest_run_endpoint(portal_settings: PortalSettings) -> None:
    _write_run(portal_settings.outputs_dir, include_notebook=True)
    client = TestClient(app)

    latest_resp = client.get("/runs/latest")
    assert latest_resp.status_code == 200
    data = latest_resp.json()
    assert data["run_id"].startswith("2025")
    assert data["notebook_exports"]


def test_run_detail_prefers_export_notebook_slug(portal_settings: PortalSettings) -> None:
    _write_run(
        portal_settings.outputs_dir,
        include_notebook=True,
        notebook_slug="custom-notebook",
    )
    client = TestClient(app)
    response = client.get("/runs/20250101-000000")
    assert response.status_code == 200
    data = response.json()
    assert data["notebook_slug"] == "custom-notebook"


def test_run_detail_falls_back_to_response_id(portal_settings: PortalSettings) -> None:
    manifest = _write_run(portal_settings.outputs_dir, include_notebook=True)
    manifest_path = portal_settings.outputs_dir / "artifacts" / "run-20250101-000000-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    exports = payload["notebook_exports"]
    for entry in exports:
        if str(entry.get("kind", "")).lower() == "preflight":
            continue
        entry["response"] = {
            "status": "ok",
            "notebook": "database-systems-poc",
            "id": "note-xyz",
        }
        break
    payload["notebook_exports"] = exports
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    client = TestClient(app)
    response = client.get("/runs/20250101-000000")
    assert response.status_code == 200
    data = response.json()
    export = data["notebook_exports"][0]
    assert export["note_id"] == "note-xyz"
    assert export["section_id"] == "note-xyz"


def test_resolve_path_blocks_outside_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True)
    repo_root = tmp_path
    allowed = outputs / "allowed.txt"
    allowed.write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")

    settings = PortalSettings(repo_root=repo_root, outputs_dir=outputs, notebook_slug=None)

    resolved_allowed = settings.resolve_path(str(allowed))
    assert resolved_allowed == allowed.resolve()

    with pytest.raises(HTTPException):
        settings.resolve_path(str(outside))


def test_course_plan_endpoint_rejects_outside_path(portal_settings: PortalSettings, tmp_path: Path) -> None:
    _write_run(portal_settings.outputs_dir, include_notebook=True)
    artifacts_dir = portal_settings.outputs_dir / "artifacts"
    manifest_path = next(artifacts_dir.glob("run-*-manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    malicious = portal_settings.outputs_dir.parent / "malicious.md"
    malicious.write_text("steal me", encoding="utf-8")
    manifest["course_plan"] = str(malicious)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    client = TestClient(app)
    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    resp = client.get(f"/runs/{run_id}/course-plan")
    assert resp.status_code == 400


def test_notebook_exports_endpoint(portal_settings: PortalSettings) -> None:
    manifest = _write_run(portal_settings.outputs_dir, include_notebook=True)
    client = TestClient(app)

    runs_resp = client.get("/runs")
    run_id = runs_resp.json()[0]["run_id"]

    response = client.get(f"/runs/{run_id}/notebook-exports")
    assert response.status_code == 200
    exports = response.json()
    assert len(exports) == 1
    entry = exports[0]
    expected_manifest_entry = _first_actual_export(manifest)
    assert entry["status"] == "ok"
    assert entry["notebook"] == "database-systems-poc"
    assert entry["title"] == expected_manifest_entry["title"]


def test_rejects_paths_outside_workspace(portal_settings: PortalSettings) -> None:
    _write_run(portal_settings.outputs_dir)
    client = TestClient(app)
    run_id = client.get("/runs").json()[0]["run_id"]

    artifacts_dir = portal_settings.outputs_dir / "artifacts"
    manifest_path = next(artifacts_dir.glob("run-*-manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    evil_path = portal_settings.outputs_dir.parent / "evil.md"
    evil_path.write_text("attack", encoding="utf-8")
    payload["course_plan"] = str(evil_path)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    response = client.get(f"/runs/{run_id}/course-plan")
    assert response.status_code == 400
