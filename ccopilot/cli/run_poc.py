"""CLI entry point for the CourseGen PoC pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List

from ccopilot.pipeline import PipelineRunArtifacts, bootstrap_pipeline, run_pipeline


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
        default=".",
        help="Repository root (default: current directory)",
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
        repo_root = _resolve_path(args.repo_root)
        os.environ.setdefault("COURSEGEN_REPO_ROOT", str(repo_root))
        config_path = _resolve_path(args.config, base=repo_root)
        constraints_path = _resolve_optional(args.constraints, base=repo_root)
        concept_override = _resolve_optional(args.concept, base=repo_root)
        dataset_override = _resolve_optional(args.dataset_dir, base=repo_root) or concept_override
        output_dir_override = _resolve_optional(args.output_dir, base=repo_root)
        world_model_store_override = _resolve_optional(args.world_model_store, base=repo_root)

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
        )
        artifacts = run_pipeline(ctx, dry_run=args.dry_run)
        _print_eval_summary(artifacts, quiet=args.quiet)
        _print_highlight_hint(artifacts, quiet=args.quiet)
        _print_notebook_hint(artifacts, quiet=args.quiet)
    except FileNotFoundError as exc:
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
    rubric_summary = _format_rubric_summary(record.get("rubrics") or [])
    print(f"[eval] overall={overall_display} | rubrics: {rubric_summary} | report={eval_path}")


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
    if not highlight_path:
        return

    if highlight_path.exists():
        source = getattr(artifacts, "highlight_source", None)
        if source == "dataset":
            label = "[highlights] (dataset)"
        elif source and source != "world_model":
            label = f"[highlights] ({source})"
        else:
            label = "[highlights]"
        print(f"{label} saved to {highlight_path}")
    else:  # pragma: no cover - defensive logging
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
        note_ids = summary.get("note_ids", []) if summary else [
            resp.get("note_id") or resp.get("id") for resp in successes if resp.get("note_id") or resp.get("id")
        ]
        queued_paths = summary.get("queued_exports", []) if summary else sorted(
            {resp.get("export_path") for resp in successes if resp.get("status") == "queued" and resp.get("export_path")}
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
            detail = f" ({len(failures)} skipped; see manifest)"
        print(f"[notebook] exported {success_count or len(successes)}/{total} sections -> {slug_display}{detail}")
    else:
        status = responses[0].get("status", "error")
        error = responses[0].get("error")
        reason = responses[0].get("reason")
        error_fragment = f", error={error}" if error else ""
        reason_fragment = f", reason={reason}" if reason else ""
        print(
            f"[notebook] export unavailable (status={status}{error_fragment}{reason_fragment}); see manifest for details"
        )


if __name__ == "__main__":
    sys.exit(main())
