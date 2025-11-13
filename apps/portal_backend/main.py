from __future__ import annotations

import copy
import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_PATTERN = re.compile(r"run-(?P<run_id>[0-9]{8}-[0-9]{6})-manifest\.json$")


class PortalSettings(BaseModel):
    """Runtime configuration for the portal backend."""

    repo_root: Path = Field(default=REPO_ROOT)
    outputs_dir: Path = Field(default=REPO_ROOT / "outputs")
    notebook_slug: str | None = Field(default=os.getenv("OPEN_NOTEBOOK_SLUG"))

    @property
    def artifacts_dir(self) -> Path:
        return (self.outputs_dir / "artifacts").resolve()

    def resolve_path(self, maybe_relative: str | None) -> Path | None:
        if not maybe_relative:
            return None
        outputs_root = self.outputs_dir.resolve()
        candidate = Path(maybe_relative)
        if not candidate.is_absolute():
            candidate = (outputs_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        try:
            candidate.relative_to(outputs_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Path {candidate} is outside of {outputs_root}.",
            ) from exc
        return candidate


@lru_cache
def get_settings() -> PortalSettings:
    outputs_dir = os.getenv("PORTAL_OUTPUTS_DIR")
    notebook_slug = os.getenv("PORTAL_NOTEBOOK_SLUG") or os.getenv("OPEN_NOTEBOOK_SLUG")
    return PortalSettings(
        outputs_dir=Path(outputs_dir).expanduser().resolve() if outputs_dir else REPO_ROOT / "outputs",
        notebook_slug=notebook_slug,
    )


class RunListItem(BaseModel):
    run_id: str
    manifest_path: str
    created_at: datetime
    has_course_plan: bool
    has_lecture: bool
    has_eval_report: bool
    overall_score: float | None = None
    notebook_export_summary: Dict[str, Any] | None = None
    highlight_source: str | None = None
    world_model_store_exists: bool | None = None
    scientific_metrics: Dict[str, Any] | None = None
    scientific_metrics_artifact: str | None = None


class TraceFile(BaseModel):
    """Metadata for downloadable trace artifacts."""

    name: str
    label: str
    path: str


class TeacherTraceMeta(BaseModel):
    path: str
    action_count: int = 0
    summary: str | None = None
    prompt: str | None = None


class NotebookExport(BaseModel):
    title: str | None = None
    citations: List[str] = Field(default_factory=list)
    status: str | None = None
    notebook: str | None = None
    note_id: str | None = None
    section_id: str | None = None
    path: str | None = None
    reason: str | None = None
    error: str | None = None


class EvaluationAttempt(BaseModel):
    iteration: int
    overall_score: float | None = None
    quiz_pass_rate: float | None = None
    failing_rubrics: List[str] = Field(default_factory=list)
    failing_questions: List[str] = Field(default_factory=list)


class RunDetail(BaseModel):
    run_id: str
    manifest_path: str
    created_at: datetime
    manifest: Dict[str, Any]
    dataset_summary: Dict[str, Any] | None = None
    ablations: Dict[str, Any] | None = None
    highlight_source: str | None = None
    world_model_store_exists: bool | None = None
    evaluation: Dict[str, Any] | None = None
    course_plan_excerpt: str | None = None
    lecture_excerpt: str | None = None
    notebook_slug: str | None = None
    notebook_exports: List[NotebookExport] = Field(default_factory=list)
    evaluation_attempts: List[EvaluationAttempt] = Field(default_factory=list)
    trace_files: List[TraceFile] = Field(default_factory=list)
    teacher_trace: TeacherTraceMeta | None = None
    scientific_metrics: Dict[str, Any] | None = None
    scientific_metrics_artifact: str | None = None


class HealthResponse(BaseModel):
    status: str
    latest_run_id: str | None = None


app = FastAPI(title="CourseGen Portal API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(settings: PortalSettings = Depends(get_settings)) -> HealthResponse:
    manifest_paths = _iter_manifest_paths(settings)
    latest = _extract_run_id(manifest_paths[0]) if manifest_paths else None
    return HealthResponse(status="ok", latest_run_id=latest)


@app.get("/runs", response_model=List[RunListItem])
def list_runs(
    limit: int = Query(50, ge=1, le=500, description="Maximum runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip before listing"),
    settings: PortalSettings = Depends(get_settings),
) -> List[RunListItem]:
    return _list_runs(settings, limit=limit, offset=offset)


@app.get("/runs/latest", response_model=RunDetail)
def get_latest_run(settings: PortalSettings = Depends(get_settings)) -> RunDetail:
    runs = _list_runs(settings, limit=1)
    if not runs:
        raise HTTPException(status_code=404, detail="No runs captured yet")
    latest = runs[0]
    return get_run_detail(latest.run_id, settings)


@app.get("/runs/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str, settings: PortalSettings = Depends(get_settings)) -> RunDetail:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    course_plan_path = _safe_resolve(settings, manifest.get("course_plan"))
    lecture_path = _safe_resolve(settings, manifest.get("lecture"))
    trace_files = collect_trace_files(run_id, manifest, settings)
    teacher_trace = build_teacher_trace_meta(manifest, settings)
    notebook_exports = _parse_notebook_exports(manifest, settings)
    evaluation_attempts = _parse_evaluation_attempts(manifest)
    notebook_slug = _infer_notebook_slug(manifest, notebook_exports, settings)

    store_exists = _derive_world_model_store_exists(manifest, settings)
    highlight_source = _derive_highlight_source(manifest, settings, store_exists=store_exists)
    sanitized_manifest = _sanitize_manifest_paths(manifest, settings)
    if highlight_source and not sanitized_manifest.get("highlight_source"):
        sanitized_manifest["highlight_source"] = highlight_source
    if store_exists is not None and "world_model_store_exists" not in sanitized_manifest:
        sanitized_manifest["world_model_store_exists"] = store_exists
    science_artifact_rel = sanitized_manifest.get("scientific_metrics_artifact")

    return RunDetail(
        run_id=run_id,
        manifest_path=_relative_to_outputs(settings, manifest_path),
        created_at=_timestamp_for(manifest_path),
        manifest=sanitized_manifest,
        dataset_summary=manifest.get("dataset_summary"),
        ablations=manifest.get("ablations"),
        highlight_source=highlight_source,
        world_model_store_exists=store_exists,
        evaluation=manifest.get("evaluation"),
        course_plan_excerpt=_read_excerpt(course_plan_path),
        lecture_excerpt=_read_excerpt(lecture_path),
        notebook_slug=notebook_slug,
        notebook_exports=notebook_exports,
        evaluation_attempts=evaluation_attempts,
        trace_files=trace_files,
        teacher_trace=teacher_trace,
        scientific_metrics=manifest.get("scientific_metrics"),
        scientific_metrics_artifact=science_artifact_rel,
    )




@app.get("/runs/{run_id}/course-plan", response_class=PlainTextResponse)
def get_course_plan(run_id: str, settings: PortalSettings = Depends(get_settings)) -> str:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    course_plan_path = settings.resolve_path(manifest.get("course_plan"))
    if not course_plan_path or not course_plan_path.exists():
        raise HTTPException(status_code=404, detail="Course plan not found for this run")
    return course_plan_path.read_text(encoding="utf-8")


@app.get("/runs/{run_id}/lecture", response_class=PlainTextResponse)
def get_lecture(run_id: str, settings: PortalSettings = Depends(get_settings)) -> str:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    lecture_path = settings.resolve_path(manifest.get("lecture"))
    if not lecture_path or not lecture_path.exists():
        raise HTTPException(status_code=404, detail="Lecture artifact not found for this run")
    return lecture_path.read_text(encoding="utf-8")


@app.get("/runs/{run_id}/notebook-exports", response_model=List[NotebookExport])
def get_notebook_exports(run_id: str, settings: PortalSettings = Depends(get_settings)) -> List[NotebookExport]:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    return _parse_notebook_exports(manifest, settings)


@app.get("/runs/{run_id}/traces/{trace_name}", response_class=PlainTextResponse)
def get_trace_file(run_id: str, trace_name: str, settings: PortalSettings = Depends(get_settings)) -> str:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    trace_files = collect_trace_files(run_id, manifest, settings)
    for trace in trace_files:
        if trace.name == trace_name:
            trace_path = settings.resolve_path(trace.path)
            if not trace_path or not trace_path.exists():
                raise HTTPException(status_code=404, detail=f"Trace file missing at {trace.path}")
            return trace_path.read_text(encoding="utf-8")
    raise HTTPException(status_code=404, detail=f"Trace '{trace_name}' not found for run {run_id}")


def _list_runs(settings: PortalSettings, *, limit: int | None = None, offset: int = 0) -> List[RunListItem]:
    items: List[RunListItem] = []
    manifest_paths = _iter_manifest_paths(settings)
    if offset:
        manifest_paths = manifest_paths[offset:]
    if limit is not None:
        manifest_paths = manifest_paths[:limit]

    for manifest_path in manifest_paths:
        try:
            manifest = _load_manifest(manifest_path)
        except ValueError:
            continue
        run_id = _extract_run_id(manifest_path)
        course_plan = _safe_resolve(settings, manifest.get("course_plan"))
        lecture = _safe_resolve(settings, manifest.get("lecture"))
        eval_report = _safe_resolve(settings, manifest.get("eval_report"))
        evaluation = manifest.get("evaluation") or {}
        notebook_summary = manifest.get("notebook_export_summary")
        store_exists = _derive_world_model_store_exists(manifest, settings)
        highlight_source = _derive_highlight_source(manifest, settings, store_exists=store_exists)
        science_artifact = _relative_manifest_path(settings, manifest.get("scientific_metrics_artifact"))

        items.append(
            RunListItem(
                run_id=run_id,
                manifest_path=_relative_to_outputs(settings, manifest_path),
                created_at=_timestamp_for(manifest_path),
                has_course_plan=bool(course_plan and course_plan.exists()),
                has_lecture=bool(lecture and lecture.exists()),
                has_eval_report=bool(eval_report and eval_report.exists()),
                overall_score=evaluation.get("overall_score"),
                notebook_export_summary=notebook_summary if isinstance(notebook_summary, dict) else None,
                highlight_source=highlight_source,
                world_model_store_exists=store_exists,
                scientific_metrics=manifest.get("scientific_metrics"),
                scientific_metrics_artifact=science_artifact,
            )
        )
    return items


def _iter_manifest_paths(settings: PortalSettings) -> List[Path]:
    artifacts_dir = settings.artifacts_dir
    if not artifacts_dir.exists():
        return []
    return sorted(artifacts_dir.glob("run-*-manifest.json"), reverse=True)


def _find_manifest_path(run_id: str, settings: PortalSettings) -> Path:
    for manifest_path in _iter_manifest_paths(settings):
        if _extract_run_id(manifest_path) == run_id:
            return manifest_path
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


def _extract_run_id(manifest_path: Path) -> str:
    match = RUN_PATTERN.search(manifest_path.name)
    if not match:
        return manifest_path.stem
    return match.group("run_id")


def _load_manifest(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Manifest missing at {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid manifest JSON: {path}") from exc


def _timestamp_for(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def collect_trace_files(run_id: str, manifest: Dict[str, Any], settings: PortalSettings) -> List[TraceFile]:
    """Aggregate available trace/provenance artifacts for a run."""

    store_exists = _derive_world_model_store_exists(manifest, settings)
    highlight = _derive_highlight_source(manifest, settings, store_exists=store_exists)
    highlight_label = _highlight_label(highlight)
    candidates = [
        ("provenance", "Provenance log", manifest.get("provenance")),
        ("evaluation", "Evaluation report", manifest.get("eval_report")),
        (
            "highlights",
            highlight_label,
            manifest.get("world_model_highlight_artifact") or manifest.get("world_model_highlights_artifact"),
        ),
        ("teacher_trace", "Teacher trace", manifest.get("teacher_trace")),
        (
            "science_metrics",
            "Scientific evaluator",
            manifest.get("scientific_metrics_artifact"),
        ),
    ]
    seen: Dict[str, TraceFile] = {}

    for name, label, raw_path in candidates:
        resolved = _safe_resolve(settings, raw_path)
        if resolved and resolved.exists():
            seen[name] = TraceFile(
                name=name,
                label=label,
                path=_relative_to_outputs(settings, resolved),
            )

    trace_dirs = [settings.outputs_dir / "traces", settings.outputs_dir / "logs"]
    for directory in trace_dirs:
        if not directory.exists():
            continue
        for candidate in directory.glob(f"*{run_id}*"):
            if not candidate.is_file():
                continue
            slug = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate.stem.lower())
            if slug not in seen:
                seen[slug] = TraceFile(
                    name=slug,
                    label=candidate.name,
                    path=_relative_to_outputs(settings, candidate.resolve()),
                )

    return list(seen.values())


def _sanitize_manifest_paths(manifest: Dict[str, Any], settings: PortalSettings) -> Dict[str, Any]:
    sanitized = copy.deepcopy(manifest)
    path_keys = [
        "course_plan",
        "lecture",
        "eval_report",
        "provenance",
        "world_model_store",
        "world_model_highlight_artifact",
        "world_model_highlights_artifact",
        "teacher_trace",
        "highlights",
        "scientific_metrics_artifact",
    ]
    for key in path_keys:
        if key in sanitized:
            sanitized[key] = _relative_manifest_path(settings, sanitized.get(key))

    notebook_exports = sanitized.get("notebook_exports")
    if isinstance(notebook_exports, list):
        for entry in notebook_exports:
            if isinstance(entry, dict) and entry.get("path"):
                entry["path"] = _relative_manifest_path(settings, entry.get("path"))
            response_payload = entry.get("response") if isinstance(entry.get("response"), dict) else None
            if response_payload and response_payload.get("export_path"):
                response_payload["export_path"] = _relative_manifest_path(
                    settings,
                    response_payload.get("export_path"),
                )

    export_summary = sanitized.get("notebook_export_summary")
    if isinstance(export_summary, dict):
        queued = export_summary.get("queued_exports")
        if isinstance(queued, list):
            export_summary["queued_exports"] = [
                _relative_manifest_path(settings, item) if isinstance(item, str) else item
                for item in queued
            ]

    return sanitized


def _relative_manifest_path(settings: PortalSettings, raw: Any) -> str | None:
    if not raw or not isinstance(raw, str):
        return None if raw in (None, "") else raw
    try:
        resolved = settings.resolve_path(raw)
    except HTTPException:
        resolved = Path(raw)
    return _relative_to_outputs(settings, resolved)


def _highlight_label(source: Any) -> str:
    label = "World-model highlights"
    if not isinstance(source, str):
        return label
    normalized = source.strip().lower()
    if normalized == "dataset":
        return "Dataset highlights"
    if normalized and normalized != "world_model":
        cleaned = normalized.replace("_", " ")
        return f"{cleaned.title()} highlights"
    return label


def _parse_notebook_exports(manifest: Dict[str, Any], settings: PortalSettings) -> List[NotebookExport]:
    entries = manifest.get("notebook_exports")
    results: List[NotebookExport] = []
    if not isinstance(entries, list):
        return results
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("kind", "")).lower() == "preflight":
            continue
        response = entry.get("response") if isinstance(entry.get("response"), dict) else None
        citations = entry.get("citations") if isinstance(entry.get("citations"), list) else []
        safe_citations = [str(cite) for cite in citations if isinstance(cite, (str, int, float))]
        if response and response.get("export_path"):
            response["export_path"] = _relative_manifest_path(settings, response["export_path"])
        response_id = response.get("id") if response else None
        note_id = response.get("note_id") if response else None
        section_id = response.get("section_id") if response else None
        if note_id is None:
            note_id = section_id or response_id
        if section_id is None:
            section_id = response_id
        resolved_path = _safe_resolve(settings, entry.get("path"))
        relative_path = None
        if resolved_path:
            try:
                relative_path = resolved_path.relative_to(settings.outputs_dir.resolve())
            except ValueError:
                relative_path = Path(resolved_path.name)
        results.append(
            NotebookExport(
                title=str(entry.get("title")) if entry.get("title") else None,
                citations=safe_citations,
                status=response.get("status") if response else None,
                notebook=response.get("notebook") if response else None,
                note_id=note_id,
                section_id=section_id,
                path=str(relative_path) if relative_path else None,
                reason=response.get("reason") if response else None,
                error=response.get("error") if response else None,
            )
        )
    return results


def _infer_notebook_slug(
    manifest: Dict[str, Any],
    notebook_exports: List[NotebookExport],
    settings: PortalSettings,
) -> str | None:
    for export in notebook_exports:
        if export.notebook:
            return export.notebook
    notebook_cfg = manifest.get("notebook")
    if isinstance(notebook_cfg, dict):
        slug = notebook_cfg.get("notebook_slug")
        if isinstance(slug, str) and slug.strip():
            return slug.strip()
    return settings.notebook_slug


def _safe_score(overall_score: Any, rubrics_payload: Any) -> float | None:
    if isinstance(overall_score, (int, float)):
        return float(overall_score)
    if isinstance(rubrics_payload, dict):
        score = rubrics_payload.get("overall_score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _safe_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _safe_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _derive_world_model_store_exists(manifest: Dict[str, Any], settings: PortalSettings) -> bool | None:
    existing = manifest.get("world_model_store_exists")
    if isinstance(existing, bool):
        return existing

    ablations = manifest.get("ablations") if isinstance(manifest.get("ablations"), dict) else None
    if isinstance(ablations, dict) and ablations.get("use_world_model") is False:
        return False

    source = manifest.get("highlight_source")
    if isinstance(source, str):
        trimmed = source.strip().lower()
        if trimmed == "world_model":
            return True
        if trimmed == "dataset":
            return False

    wm_highlights = manifest.get("world_model_highlights")
    if isinstance(wm_highlights, dict) and wm_highlights:
        return True

    store_path = _safe_resolve(settings, manifest.get("world_model_store"))
    if store_path is not None:
        return store_path.exists()

    return None


def _derive_highlight_source(
    manifest: Dict[str, Any],
    settings: PortalSettings,
    *,
    store_exists: bool | None = None,
) -> str | None:
    source = manifest.get("highlight_source")
    if isinstance(source, str):
        trimmed = source.strip()
        if trimmed:
            return trimmed

    ablations = manifest.get("ablations") if isinstance(manifest.get("ablations"), dict) else None
    if store_exists is None:
        store_exists = _derive_world_model_store_exists(manifest, settings)

    if store_exists is True:
        return "world_model"

    if isinstance(ablations, dict) and ablations.get("use_world_model") is False:
        return "dataset"

    if store_exists is False:
        return "dataset"

    wm_highlights = manifest.get("world_model_highlights")
    if isinstance(wm_highlights, dict) and wm_highlights:
        return "world_model"

    return None


def _parse_evaluation_attempts(manifest: Dict[str, Any]) -> List[EvaluationAttempt]:
    evaluation = manifest.get("evaluation")
    attempts = evaluation.get("attempts") if isinstance(evaluation, dict) else None
    if not isinstance(attempts, list):
        return []

    parsed: List[EvaluationAttempt] = []
    for entry in attempts:
        if not isinstance(entry, dict):
            continue

        iteration = entry.get("iteration")
        if not isinstance(iteration, int):
            continue

        rubrics_payload = entry.get("rubrics")
        overall_score = _safe_score(entry.get("overall_score"), rubrics_payload)

        quiz = entry.get("quiz") if isinstance(entry.get("quiz"), dict) else None
        quiz_pass = _safe_float(quiz.get("pass_rate")) if quiz else None

        mutation = entry.get("triggered_mutation") if isinstance(entry.get("triggered_mutation"), dict) else {}
        failing_rubrics = mutation.get("failing_rubrics")
        failing_questions = mutation.get("failing_questions")

        if not failing_rubrics:
            failing_rubrics = entry.get("failing_rubrics")
        if not failing_questions:
            failing_questions = entry.get("failing_questions")

        parsed.append(
            EvaluationAttempt(
                iteration=iteration,
                overall_score=overall_score,
                quiz_pass_rate=quiz_pass,
                failing_rubrics=_safe_str_list(failing_rubrics),
                failing_questions=_safe_str_list(failing_questions),
            )
        )
    return parsed


def _safe_resolve(settings: PortalSettings, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    try:
        return settings.resolve_path(raw_path)
    except HTTPException:
        return None


def _relative_to_outputs(settings: PortalSettings, path: Path | None) -> str | None:
    if not path:
        return None
    try:
        return str(path.resolve().relative_to(settings.outputs_dir.resolve()))
    except ValueError:
        return path.name


def _read_excerpt(path: Path | None, *, limit: int = 400) -> str | None:
    if not path or not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    snippet = text.strip().splitlines()
    preview = "\n".join(snippet[: min(8, len(snippet))])
    if len(text) <= limit:
        return preview
    return preview[:limit].rstrip() + "…"


@app.exception_handler(HTTPException)
async def http_error_handler(_: Any, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def build_teacher_trace_meta(manifest: Dict[str, Any], settings: PortalSettings) -> TeacherTraceMeta | None:
    trace_path = _safe_resolve(settings, manifest.get("teacher_trace"))
    if not trace_path or not trace_path.exists():
        return None
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return TeacherTraceMeta(path=str(trace_path))

    actions = payload.get("actions") if isinstance(payload, dict) else []
    action_count = len(actions) if isinstance(actions, list) else 0
    summary = payload.get("summary") if isinstance(payload, dict) else None
    prompt = payload.get("prompt") if isinstance(payload, dict) else None

    return TeacherTraceMeta(
        path=str(trace_path),
        action_count=action_count,
        summary=summary if isinstance(summary, str) else None,
        prompt=str(prompt) if isinstance(prompt, str) else None,
    )
