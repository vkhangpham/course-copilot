"""CLI entry point for the CourseGen PoC pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List

from ccopilot.core.validation import ValidationFailure, strict_validation, validate_handcrafted_dataset
from ccopilot.pipeline import PipelineRunArtifacts, bootstrap_pipeline, run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CourseGen PoC orchestration pipeline.")
    parser.add_argument(
        "--config",
        default="config/pipeline.yaml",
        help="Path to the pipeline YAML (default: config/pipeline.yaml)",
    )
    parser.add_argument(
        "--constraints",
        default=None,
        help="Optional course constraints YAML that overrides the pipeline config.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help=f"Repository root (default: {REPO_ROOT})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated artifacts (default: <repo-root>/outputs)",
    )
    parser.add_argument(
        "--dataset-dir",
        default=None,
        help="Override the dataset directory defined in config.world_model.dataset_dir",
    )
    parser.add_argument(
        "--concept",
        default=None,
        help="Alias for --dataset-dir (matches docs runbook).",
    )
    parser.add_argument(
        "--world-model-store",
        default=None,
        help="Override the SQLite world-model store path defined in config.world_model.sqlite_path",
    )
    parser.add_argument(
        "--science-config",
        default=None,
        help=("Override the scientific evaluator config (defaults to config/scientific_config.yaml when present)."),
    )
    parser.add_argument(
        "--notebook",
        default=None,
        help="Override the notebook slug used for Open Notebook exports.",
    )
    parser.add_argument(
        "--skip-notebook-create",
        action="store_true",
        help="Do not auto-create the Open Notebook slug before publishing.",
    )
    parser.add_argument(
        "--ablations",
        default=None,
        help="Comma-separated list of ablations (no_world_model,no_students,no_recursion)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate config and log bootstrap info without invoking the orchestrator.",
    )
    parser.add_argument(
        "--ingest-world-model",
        action="store_true",
        help="Rebuild the SQLite world model from the handcrafted dataset before running.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress evaluation/highlight summaries on stdout.",
    )
    parser.add_argument(
        "--offline-teacher",
        action="store_true",
        help="Skip the vendor Teacher RLM and force COURSEGEN_RLM_OFFLINE=1 for deterministic runs.",
    )
    return parser


def _resolve_path(value: str | Path, *, base: Path | None = None) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    anchor = Path(base).expanduser().resolve() if base is not None else Path.cwd()
    return (anchor / candidate).resolve()


def _resolve_optional(value: str | Path | None, *, base: Path | None = None) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value, base=base)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.offline_teacher:
            os.environ["COURSEGEN_RLM_OFFLINE"] = "1"
        repo_root = _resolve_path(args.repo_root)
        os.environ["COURSEGEN_REPO_ROOT"] = str(repo_root)
        config_path = _resolve_path(args.config, base=repo_root)
        constraints_path = _resolve_optional(args.constraints, base=repo_root)
        concept_override = _resolve_optional(args.concept, base=repo_root)
        dataset_override = _resolve_optional(args.dataset_dir, base=repo_root) or concept_override
        output_dir_override = _resolve_optional(args.output_dir, base=repo_root)
        world_model_store_override = _resolve_optional(args.world_model_store, base=repo_root)
        science_config_override = _resolve_optional(args.science_config, base=repo_root)

        strict_validation.validate_file_exists(config_path)
        if constraints_path is not None:
            strict_validation.validate_file_exists(constraints_path)
        if science_config_override is not None:
            strict_validation.validate_file_exists(science_config_override)
        if dataset_override is not None:
            validate_handcrafted_dataset(dataset_override)

        ctx = bootstrap_pipeline(
            config_path=config_path,
            repo_root=repo_root,
            output_dir=output_dir_override,
            ablations=args.ablations,
            dataset_dir_override=dataset_override,
            world_model_store_override=world_model_store_override,
            ingest_before_run=args.ingest_world_model,
            constraints_path=constraints_path,
            notebook_slug_override=args.notebook,
            notebook_auto_create_override=False if args.skip_notebook_create else None,
            science_config_path=science_config_override,
        )
        artifacts = run_pipeline(ctx, dry_run=args.dry_run)
        _print_eval_summary(artifacts, quiet=args.quiet)
        _print_scientific_summary(artifacts, quiet=args.quiet)
        _print_highlight_hint(artifacts, quiet=args.quiet)
        _print_notebook_hint(artifacts, quiet=args.quiet)
        _print_artifact_summary(artifacts, quiet=args.quiet)
    except (FileNotFoundError, ValidationFailure, ValueError) as exc:
        parser.error(str(exc))
    except Exception as exc:  # noqa: BLE001 - bubble up to CLI for now
        print(f"[run_poc] error: {exc}", file=sys.stderr)
        return 1

    return 0


def _print_eval_summary(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    """Emit a human-readable evaluation summary for CLI users."""

    if artifacts is None or quiet:
        return

    eval_path = artifacts.eval_report
    if not eval_path.exists():
        print(f"[eval] report missing at {eval_path}")
        return

    try:
        record = _load_eval_record(eval_path)
    except ValueError as exc:
        print(f"[eval] unable to read {eval_path}: {exc}")
        return

    if not record.get("use_students"):
        status = record.get("status", "students_disabled")
        print(f"[eval] student graders skipped ({status}); report={eval_path}")
        return

    overall = record.get("overall_score")
    overall_display = _format_score(overall)
    engines: list[str] = []
    rubric_engine = record.get("rubric_engine")
    quiz_engine = record.get("quiz_engine")
    if rubric_engine:
        engines.append(f"rubric={rubric_engine}")
    if quiz_engine:
        engines.append(f"quiz={quiz_engine}")
    engine_hint = f" ({', '.join(engines)})" if engines else ""
    rubric_summary = _format_rubric_summary(record.get("rubrics") or [])
    print(f"[eval] overall={overall_display}{engine_hint} | rubrics: {rubric_summary} | report={eval_path}")


def _print_scientific_summary(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    """Summarize scientific evaluation metrics on stdout."""

    if artifacts is None or quiet:
        return

    metrics = getattr(artifacts, "scientific_metrics", None)
    if not metrics:
        return

    pedagogical: dict[str, Any] = metrics.get("pedagogical") or {}
    content: dict[str, Any] = metrics.get("content_quality") or {}
    outcomes: dict[str, Any] = metrics.get("learning_outcomes") or {}

    parts: list[str] = []
    blooms = pedagogical.get("blooms_alignment")
    coherence = pedagogical.get("learning_path_coherence")
    citations = content.get("citation_validity")
    citation_coverage = content.get("citation_coverage")
    retention = outcomes.get("predicted_retention")

    if blooms is not None:
        parts.append(f"blooms={_format_score(blooms)}")
    if coherence is not None:
        parts.append(f"coherence={_format_score(coherence)}")
    if citations is not None:
        parts.append(f"citations={_format_score(citations)}")
    if citation_coverage is not None:
        parts.append(f"cite_cov={_format_score(citation_coverage)}")
    if retention is not None:
        parts.append(f"retention={_format_score(retention)}")

    summary = " | ".join(parts) if parts else "no scientific metrics"
    print(f"[science] {summary}")


def _load_eval_record(path: Path) -> dict[str, Any]:
    line = path.read_text(encoding="utf-8").splitlines()
    if not line:
        raise ValueError("empty evaluation file")
    try:
        return json.loads(line[0])
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError("invalid JSON in evaluation file") from exc


def _format_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return str(value) if value is not None else "n/a"


def _format_rubric_summary(rubrics: Iterable[dict[str, Any]]) -> str:
    items = []
    for rubric in rubrics:
        name = str(rubric.get("name", "?"))
        score = _format_score(rubric.get("score"))
        passed = "PASS" if rubric.get("passed") else "FAIL"
        items.append(f"{name}:{passed}({score})")
    return ", ".join(items) if items else "no rubrics"


def _print_highlight_hint(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    """Surface the highlight artifact path (if any) after the run."""

    if artifacts is None or quiet:
        return

    highlight_path = getattr(artifacts, "highlights", None)
    source = getattr(artifacts, "highlight_source", None)
    label = "[highlights]"
    if source:
        label = f"[highlights] ({source})"

    if highlight_path and highlight_path.exists():
        print(f"{label} saved to {highlight_path}")
    elif source:
        print(f"{label} not generated (no highlight artifact)")
    elif highlight_path:  # pragma: no cover - defensive logging
        print(f"[highlights] expected at {highlight_path} (missing)")


def _print_notebook_hint(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    if artifacts is None or quiet:
        return

    exports: List[dict[str, Any]] | None = getattr(artifacts, "notebook_exports", None)
    if not exports:
        return

    summary = getattr(artifacts, "notebook_export_summary", None)

    responses: List[dict[str, Any]] = []
    for entry in exports:
        if isinstance(entry, dict):
            if entry.get("kind") == "preflight":
                continue
            response = entry.get("response")
            if isinstance(response, dict):
                responses.append(response)
                continue
            responses.append(entry)
        else:
            responses.append({})

    if not responses:
        return

    successes = [resp for resp in responses if resp.get("status") not in {"error", "skipped"}]
    failures = [resp for resp in responses if resp.get("status") in {"error", "skipped"}]
    target = next(
        (resp.get("notebook") or resp.get("notebook_slug") for resp in responses if resp),
        None,
    )
    total = summary.get("total") if summary else len(responses)
    success_count = summary.get("success") if summary else len(successes)
    if successes:
        slug_display = target or "notebook"
        note_ids = (
            summary.get("note_ids", [])
            if summary
            else [resp.get("note_id") or resp.get("id") for resp in successes if resp.get("note_id") or resp.get("id")]
        )
        queued_paths = (
            summary.get("queued_exports", [])
            if summary
            else sorted({resp.get("export_path") for resp in successes if resp.get("status") == "queued" and resp.get("export_path")})
        )
        detail = ""
        if note_ids:
            preview = ", ".join(note_ids[:3])
            if len(note_ids) > 3:
                preview += ", …"
            detail = f" (notes: {preview})"
        elif queued_paths:
            detail = f" (queued at {', '.join(queued_paths)})"
        elif failures:
            error_count = sum(1 for resp in failures if str(resp.get("status", "")).lower() == "error")
            skipped_count = sum(1 for resp in failures if str(resp.get("status", "")).lower() == "skipped")
            labels: list[str] = []
            if error_count:
                labels.append(f"{error_count} error{'s' if error_count != 1 else ''}")
            if skipped_count:
                labels.append(f"{skipped_count} skipped")
            if not labels:
                labels.append(f"{len(failures)} issue(s)")
            detail = f" ({', '.join(labels)}; see manifest)"
        print(f"[notebook] exported {success_count or len(successes)}/{total} sections -> {slug_display}{detail}")
    else:
        status = responses[0].get("status", "error")
        error = responses[0].get("error")
        reason = responses[0].get("reason")
        error_fragment = f", error={error}" if error else ""
        reason_fragment = f", reason={reason}" if reason else ""
        print(f"[notebook] export unavailable (status={status}{error_fragment}{reason_fragment}); see manifest for details")


def _print_artifact_summary(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    """Emit a concise map of key artifact paths for reproducibility."""

    if artifacts is None or quiet:
        return

    science_candidate = getattr(artifacts, "scientific_metrics_path", None)
    if not science_candidate:
        science_candidate = _read_science_path_from_manifest(getattr(artifacts, "manifest", None))

    science_config_candidate = getattr(artifacts, "science_config_path", None)
    if not science_config_candidate:
        science_config_candidate = _read_science_config_from_manifest(getattr(artifacts, "manifest", None))

    entries: list[str] = []
    for label, value in (
        ("course_plan", getattr(artifacts, "course_plan", None)),
        ("lecture", getattr(artifacts, "lecture", None)),
        ("manifest", getattr(artifacts, "manifest", None)),
        ("eval_report", getattr(artifacts, "eval_report", None)),
        ("provenance", getattr(artifacts, "provenance", None)),
        ("science", science_candidate),
        ("science_config", science_config_candidate),
    ):
        formatted = _stringify_path(value)
        if formatted:
            entries.append(f"{label}={formatted}")

    if entries:
        print(f"[artifacts] {' | '.join(entries)}")

    trace_path = _stringify_path(getattr(artifacts, "teacher_trace", None))
    teacher_mode = getattr(artifacts, "teacher_rlm_mode", None)
    teacher_reason = getattr(artifacts, "teacher_rlm_reason", None)
    if trace_path or teacher_mode or teacher_reason:
        fragments: list[str] = []
        if teacher_mode:
            fragments.append(f"mode={teacher_mode}")
        if teacher_reason:
            fragments.append(f"reason={teacher_reason}")
        if trace_path:
            fragments.append(f"trace={trace_path}")
        print(f"[teacher] {' | '.join(fragments)}")

    _print_stage_error_summary(artifacts, quiet=quiet)


def _stringify_path(path_value: Path | str | None) -> str | None:
    if not path_value:
        return None
    return str(Path(path_value).expanduser().resolve())


def _read_manifest_path(manifest_path: Path | str | None, field: str) -> Path | None:
    payload = _load_manifest_json(manifest_path)
    if payload is None:
        return None
    entry = payload.get(field)
    return Path(entry) if isinstance(entry, str) else None


def _read_science_path_from_manifest(manifest_path: Path | str | None) -> Path | None:
    return _read_manifest_path(manifest_path, "scientific_metrics_artifact")


def _read_science_config_from_manifest(manifest_path: Path | str | None) -> Path | None:
    return _read_manifest_path(manifest_path, "science_config_path")


def _read_stage_errors_from_manifest(manifest_path: Path | str | None) -> list[dict[str, object]]:
    payload = _load_manifest_json(manifest_path)
    if payload is None:
        return []
    errors = payload.get("stage_errors")
    if isinstance(errors, list):
        return [entry for entry in errors if isinstance(entry, dict)]
    return []


def _print_stage_error_summary(artifacts: PipelineRunArtifacts | None, *, quiet: bool = False) -> None:
    if artifacts is None or quiet:
        return
    manifest_path = getattr(artifacts, "manifest", None)
    errors = _read_stage_errors_from_manifest(manifest_path)
    if not errors:
        return
    preview = "; ".join(_format_stage_error(entry) for entry in errors[:2])
    if len(errors) > 2:
        preview += ", …"
    print(f"[stage-errors] {len(errors)} issue(s) recorded ({preview}) | see manifest")


def _format_stage_error(entry: dict[str, object]) -> str:
    stage = entry.get("stage") or entry.get("phase") or "stage"
    message = entry.get("message") or entry.get("error") or entry.get("reason")
    return f"{stage}: {message}" if message else str(stage)


def _load_manifest_json(manifest_path: Path | str | None) -> dict[str, object] | None:
    if not manifest_path:
        return None
    path = Path(manifest_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:  # pragma: no cover - defensive
        return None
    return payload if isinstance(payload, dict) else None


if __name__ == "__main__":
    sys.exit(main())
