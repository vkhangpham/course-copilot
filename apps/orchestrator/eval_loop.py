"""Standalone entry point for the grader/self-evolving loop."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Run graders against generated course artifacts.")


@app.command()
def run(
    artifacts_dir: Path = typer.Option(Path("outputs"), help="Run outputs to evaluate."),
    rubric: Path = typer.Option(Path("config/rubrics.yaml"), help="Rubric config file."),
) -> None:
    """Placeholder for the evaluation workflow (implemented in ccopilot-syy)."""

    typer.echo(
        f"Eval loop not yet implemented. Provide artifacts at {artifacts_dir} and rubric {rubric}."
    )


if __name__ == "__main__":
    app()
