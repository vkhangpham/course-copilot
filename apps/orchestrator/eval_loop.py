"""Standalone entry point for the grader/self-evolving loop."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import typer

try:  # pragma: no cover - fallback when executed as a script
    from .students import StudentGraderPool
except ImportError:  # pragma: no cover
    from apps.orchestrator.students import StudentGraderPool


ENV_REPO_ROOT = "COURSEGEN_REPO_ROOT"
_MODULE_REPO_ROOT = Path(__file__).resolve().parents[2]


app = typer.Typer(help="Run graders against generated course artifacts.")


def _resolve(base: Path, maybe_relative: Path) -> Path:
    return maybe_relative.expanduser().resolve() if maybe_relative.is_absolute() else (base / maybe_relative).resolve()


def _normalize_sources(sources: List[str]) -> List[str]:
    return [source.strip() for source in sources if source.strip()]


def _resolve_repo_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    env_root = os.environ.get(ENV_REPO_ROOT)
    if env_root:
        return Path(env_root).expanduser().resolve()
    return _MODULE_REPO_ROOT


@app.command()
def run(
    repo_root: Path | None = typer.Option(
        None,
        "--repo-root",
        help="Repository root used to resolve default artifacts/rubrics (defaults to repo containing this module).",
    ),
    artifacts_dir: Path | None = typer.Option(
        None,
        "--artifacts-dir",
        help="Directory containing generated artifacts (defaults to <repo-root>/outputs).",
    ),
    lectures_dir: Path = typer.Option(
        Path("lectures"),
        help="Path to lecture markdown files. Relative paths are resolved within the artifacts directory.",
    ),
    rubric: Path | None = typer.Option(
        None,
        "--rubric",
        help="Rubric config file (defaults to <repo-root>/evals/rubrics.yaml).",
    ),
    output_dir: Path | None = typer.Option(
        None,
        help="Directory where evaluation JSONL results should be written (defaults to <artifacts>/evaluations).",
    ),
    pattern: str = typer.Option("*.md", help="Glob pattern for lecture artifacts."),
    required_source: List[str] = typer.Option(
        [],
        "--required-source",
        "-s",
        help="Optional canonical source identifiers the grader should enforce.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Suppress the final summary line (artifacts/evaluations are still written).",
    ),
) -> None:
    """Evaluate generated lectures with the lightweight student grader."""

    repo_root = _resolve_repo_root(repo_root)
    os.environ[ENV_REPO_ROOT] = str(repo_root)
    artifacts_dir = (artifacts_dir or (repo_root / "outputs")).expanduser().resolve()
    lectures_dir = _resolve(artifacts_dir, lectures_dir)
    rubric = (rubric or (repo_root / "evals" / "rubrics.yaml")).expanduser().resolve()
    output_dir = (output_dir.expanduser().resolve() if output_dir else artifacts_dir / "evaluations")
    output_dir.mkdir(parents=True, exist_ok=True)

    required_sources = _normalize_sources(required_source)

    try:
        grader = StudentGraderPool.from_yaml(rubric, required_sources=required_sources)
    except FileNotFoundError:
        typer.echo(f"Rubric file not found: {rubric}", err=True)
        raise typer.Exit(code=2) from None
    except ValueError as exc:
        typer.echo(f"Invalid rubric definition in {rubric}: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    lecture_paths = sorted(lectures_dir.glob(pattern))
    if not lecture_paths:
        typer.echo(
            f"No lecture artifacts found under {lectures_dir} matching pattern '{pattern}'.",
            err=True,
        )
        raise typer.Exit(code=1)

    records = []
    failing = 0
    for lecture in lecture_paths:
        results = grader.evaluate(lecture)
        if any(not rubric_result["passed"] for rubric_result in results.get("rubrics", [])):
            failing += 1
        records.append(
            {
                "artifact": str(lecture),
                "results": results,
                "rubrics_path": str(rubric),
                "required_sources": required_sources,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"eval-{timestamp}.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    if not quiet:
        typer.echo(
            f"Evaluated {len(records)} artifact(s); {failing} did not meet rubric thresholds. Results → {output_path}"
        )


if __name__ == "__main__":
    app()
