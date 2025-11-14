"""Minimal CourseGen CLI that forwards to ccopilot.cli.run_poc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.orchestrator.ta_roles.dataset_paths import resolve_dataset_root
from ccopilot.cli.run_poc import main as _cli_main

DEFAULT_CONFIG_REL = Path("config") / "pipeline.yaml"
DEFAULT_CONSTRAINTS_REL = Path("config") / "course_config.yaml"
DEFAULT_CONCEPTS_REL = Path("data") / "handcrafted" / "database_systems"
DEFAULT_SCIENCE_CONFIG_REL = Path("config") / "scientific_config.yaml"
ABLATION_CHOICES = ("no_world_model", "no_students", "no_recursion")

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    """Return the minimalist CourseGen CLI described in AGENTS.md."""

    parser = argparse.ArgumentParser(
        description="Run the CourseGen pipeline with only the required inputs.",
    )
    parser.add_argument(
        "--constraints",
        default=None,
        help=f"Course constraints YAML (defaults to {DEFAULT_CONSTRAINTS_REL}).",
    )
    parser.add_argument(
        "--concepts",
        "--concept",
        dest="concepts",
        default=None,
        help=(
            f"Directory containing handcrafted world-model artifacts (defaults to {DEFAULT_CONCEPTS_REL}). "
            "Supports the legacy --concept alias."
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
            f"Comma-separated list of ablations to enable ({', '.join(ABLATION_CHOICES)}). Leave empty to run with all subsystems enabled."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help=argparse.SUPPRESS,
    )
    return parser


def _resolve_path(value: str | Path, *, base: Path | None = None) -> Path:
    """Return an absolute path, anchoring relatives to ``base`` when provided."""

    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    anchor = Path(base).expanduser().resolve() if base is not None else Path.cwd()
    return (anchor / candidate).resolve()


def _resolve_optional_path(value: str | Path | None, *, base: Path | None = None) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value, base=base)


def _resolve_dataset_path(args: argparse.Namespace, repo_root: Path) -> Path | None:
    explicit = _resolve_optional_path(args.concepts, base=repo_root)
    if explicit is not None:
        return explicit

    candidate = resolve_dataset_root(repo_root=repo_root)
    return candidate if candidate.exists() else None


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = _resolve_path(args.repo_root)
    config_path = (repo_root / DEFAULT_CONFIG_REL).resolve()
    constraints_default = (repo_root / DEFAULT_CONSTRAINTS_REL).resolve()
    science_default = (repo_root / DEFAULT_SCIENCE_CONFIG_REL).resolve()
    dataset_path = _resolve_dataset_path(args, repo_root)

    constraints_path = _resolve_optional_path(args.constraints, base=repo_root)
    if constraints_path is None and constraints_default.exists():
        constraints_path = constraints_default

    science_config_path = science_default if science_default.exists() else None

    forwarded: list[str] = [
        "--config",
        str(config_path),
        "--repo-root",
        str(repo_root),
        "--notebook",
        args.notebook,
    ]

    if constraints_path is not None:
        forwarded.extend(["--constraints", str(constraints_path)])
    if dataset_path is not None:
        forwarded.extend(["--concept", str(dataset_path)])
    if science_config_path is not None:
        forwarded.extend(["--science-config", str(science_config_path)])
    if args.ablations:
        forwarded.extend(["--ablations", args.ablations])

    return _cli_main(forwarded)


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
