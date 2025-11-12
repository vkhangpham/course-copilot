"""CLI entry point for the CourseGen PoC pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from ccopilot.pipeline import PipelineRunArtifacts, bootstrap_pipeline, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CourseGen PoC orchestration pipeline.")
    parser.add_argument(
        "--config",
        default="config/pipeline.yaml",
        help="Path to the pipeline YAML (default: config/pipeline.yaml)",
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
        "--world-model-store",
        default=None,
        help="Override the SQLite world-model store path defined in config.world_model.sqlite_path",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        ctx = bootstrap_pipeline(
            config_path=Path(args.config),
            repo_root=Path(args.repo_root),
            output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
            ablations=args.ablations,
            dataset_dir_override=Path(args.dataset_dir).resolve() if args.dataset_dir else None,
            world_model_store_override=Path(args.world_model_store).resolve()
            if args.world_model_store
            else None,
            ingest_before_run=args.ingest_world_model,
        )
        artifacts = run_pipeline(ctx, dry_run=args.dry_run)
        _print_eval_summary(artifacts)
        _print_highlight_hint(artifacts)
        _print_highlight_hint(artifacts)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except Exception as exc:  # noqa: BLE001 - bubble up to CLI for now
        print(f"[run_poc] error: {exc}", file=sys.stderr)
        return 1

    return 0


def _print_eval_summary(artifacts: PipelineRunArtifacts | None) -> None:
    """Emit a human-readable evaluation summary for CLI users."""

    if artifacts is None:
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


def _print_highlight_hint(artifacts: PipelineRunArtifacts | None) -> None:
    if artifacts is None:
        return

    highlight_path = artifacts.highlights
    if not highlight_path:
        return

    if highlight_path.exists():
        print(f"[highlights] saved to {highlight_path}")
    else:
        print(f"[highlights] expected at {highlight_path} (missing)")


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


def _print_highlight_hint(artifacts: PipelineRunArtifacts | None) -> None:
    """Surface the highlight artifact path (if any) after the run."""

    if artifacts is None:
        return

    highlight_path = getattr(artifacts, "highlights", None)
    if not highlight_path:
        return

    if highlight_path.exists():
        print(f"[highlights] saved to {highlight_path}")
    else:  # pragma: no cover - defensive logging
        print(f"[highlights] expected at {highlight_path} (missing)")


if __name__ == "__main__":
    sys.exit(main())
