"""CLI entry point for the CourseGen PoC pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ccopilot.pipeline import bootstrap_pipeline, run_pipeline


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
        run_pipeline(ctx, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except Exception as exc:  # noqa: BLE001 - bubble up to CLI for now
        print(f"[run_poc] error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
