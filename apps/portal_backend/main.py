from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException
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
        candidate = Path(maybe_relative)
        if not candidate.is_absolute():
            candidate = (self.repo_root / candidate).resolve()
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


class RunDetail(BaseModel):
    run_id: str
    manifest_path: str
    created_at: datetime
    manifest: Dict[str, Any]
    dataset_summary: Dict[str, Any] | None = None
    ablations: Dict[str, Any] | None = None
    evaluation: Dict[str, Any] | None = None
    course_plan_excerpt: str | None = None
    lecture_excerpt: str | None = None
    notebook_slug: str | None = None


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
    runs = _list_runs(settings)
    latest = runs[0].run_id if runs else None
    return HealthResponse(status="ok", latest_run_id=latest)


@app.get("/runs", response_model=List[RunListItem])
def list_runs(settings: PortalSettings = Depends(get_settings)) -> List[RunListItem]:
    return _list_runs(settings)


@app.get("/runs/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str, settings: PortalSettings = Depends(get_settings)) -> RunDetail:
    manifest_path = _find_manifest_path(run_id, settings)
    manifest = _load_manifest(manifest_path)
    course_plan_path = settings.resolve_path(manifest.get("course_plan"))
    lecture_path = settings.resolve_path(manifest.get("lecture"))

    return RunDetail(
        run_id=run_id,
        manifest_path=str(manifest_path),
        created_at=_timestamp_for(manifest_path),
        manifest=manifest,
        dataset_summary=manifest.get("dataset_summary"),
        ablations=manifest.get("ablations"),
        evaluation=manifest.get("evaluation"),
        course_plan_excerpt=_read_excerpt(course_plan_path),
        lecture_excerpt=_read_excerpt(lecture_path),
        notebook_slug=settings.notebook_slug,
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


def _list_runs(settings: PortalSettings) -> List[RunListItem]:
    items: List[RunListItem] = []
    for manifest_path in _iter_manifest_paths(settings):
        try:
            manifest = _load_manifest(manifest_path)
        except ValueError:
            continue
        run_id = _extract_run_id(manifest_path)
        course_plan = settings.resolve_path(manifest.get("course_plan"))
        lecture = settings.resolve_path(manifest.get("lecture"))
        eval_report = settings.resolve_path(manifest.get("eval_report"))
        evaluation = manifest.get("evaluation") or {}
        items.append(
            RunListItem(
                run_id=run_id,
                manifest_path=str(manifest_path),
                created_at=_timestamp_for(manifest_path),
                has_course_plan=bool(course_plan and course_plan.exists()),
                has_lecture=bool(lecture and lecture.exists()),
                has_eval_report=bool(eval_report and eval_report.exists()),
                overall_score=evaluation.get("overall_score"),
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
