"""Minimal CourseGen CLI that forwards to ccopilot.cli.run_poc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ccopilot.cli.run_poc import main as _cli_main

DEFAULT_CONFIG_REL = Path("config") / "pipeline.yaml"
DEFAULT_CONSTRAINTS_REL = Path("config") / "course_config.yaml"
DEFAULT_CONCEPTS_REL = Path("data") / "handcrafted" / "database_systems"
DEFAULT_OUTPUT_REL = Path("outputs")
ABLATION_CHOICES = ("no_world_model", "no_students", "no_recursion")

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    """Return the slim CLI parser described in AGENTS.md."""

    parser = argparse.ArgumentParser(
        description="Run the CourseGen pipeline with the minimal flag set (constraints + concepts + notebook).",
    )
    parser.add_argument(
        "--constraints",
        default=None,
        help=f"Course constraints YAML (defaults to {DEFAULT_CONSTRAINTS_REL}).",
    )
    parser.add_argument(
        "--concepts",
        default=None,
        help=(
            "Path to the handcrafted concept/world-model dataset "
            f"(defaults to {DEFAULT_CONCEPTS_REL})."
        ),
    )
    parser.add_argument(
        "--notebook",
        default="database-systems-poc",
        help="Notebook slug to publish into (defaults to database-systems-poc).",
    )
    parser.add_argument(
        "--ablations",
        default=None,
        help=(
            "Comma-separated list of ablations to enable "
            f"({', '.join(ABLATION_CHOICES)}). Leave empty to run with all subsystems enabled."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated artifacts (defaults to <repo>/outputs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config/dataset and log bootstrap info without invoking the orchestrator.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the CLI evaluation/highlight summaries (artifacts are still written).",
    )
    parser.add_argument(
        "--ingest-world-model",
        action="store_true",
        help="Rebuild the SQLite world model snapshot before running (mirrors coursegen-poc flag).",
    )
    parser.add_argument(
        "--skip-notebook-create",
        action="store_true",
        help="Skip auto-creating the Open Notebook slug before publishing.",
    )
    # Advanced overrides stay hidden so the help output matches the “minimal CLI” promise.
    parser.add_argument(
        "--config",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help=argparse.SUPPRESS,
    )
    return parser


def _resolve_path(value: str | Path | None, default: Path, *, base: Path | None = None) -> Path:
    """Return an absolute path, anchoring relatives to ``base`` when provided."""

    candidate = Path(value) if value else Path(default)
    candidate = candidate.expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    base_path = Path(base).expanduser().resolve() if base is not None else Path.cwd()
    return (base_path / candidate).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = _resolve_path(args.repo_root, REPO_ROOT)
    config_default = (repo_root / DEFAULT_CONFIG_REL).resolve()
    constraints_default = (repo_root / DEFAULT_CONSTRAINTS_REL).resolve()
    concepts_default = (repo_root / DEFAULT_CONCEPTS_REL).resolve()
    output_default = (repo_root / DEFAULT_OUTPUT_REL).resolve()

    config_path = _resolve_path(args.config, config_default, base=repo_root)
    output_dir = _resolve_path(args.output_dir, output_default, base=repo_root)
    constraints_path = _resolve_path(args.constraints, constraints_default, base=repo_root)
    concepts_path = _resolve_path(args.concepts, concepts_default, base=repo_root)

    user_supplied_constraints = args.constraints is not None
    user_supplied_concepts = args.concepts is not None

    forwarded: list[str] = [
        "--config",
        str(config_path),
        "--repo-root",
        str(repo_root),
        "--output-dir",
        str(output_dir),
    ]

    if user_supplied_constraints or constraints_path.exists():
        forwarded.extend(["--constraints", str(constraints_path)])
    if user_supplied_concepts or concepts_path.exists():
        forwarded.extend(["--concept", str(concepts_path)])
    forwarded.extend(["--notebook", args.notebook])
    if args.ablations:
        forwarded.extend(["--ablations", args.ablations])
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.quiet:
        forwarded.append("--quiet")
    if args.ingest_world_model:
        forwarded.append("--ingest-world-model")
    if args.skip_notebook_create:
        forwarded.append("--skip-notebook-create")

    return _cli_main(forwarded)


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
