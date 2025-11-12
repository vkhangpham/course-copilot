"""Validate handcrafted Database Systems dataset assets."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from scripts.handcrafted_loader import load_dataset, validate_dataset

app = typer.Typer(help="Lint the handcrafted dataset for referential integrity issues.")
console = Console()


@app.command()
def validate(
    dataset_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    fail_on_warning: bool = typer.Option(
        False, "--fail-on-warning", help="Exit non-zero when warnings are present."
    ),
) -> None:
    dataset = load_dataset(dataset_dir)
    errors, warnings = validate_dataset(dataset)
    table = Table(title="Handcrafted Dataset Validation", show_header=True)
    table.add_column("Severity", justify="center")
    table.add_column("Message")
    for issue in errors:
        table.add_row("error", issue, style="bold red")
    for issue in warnings:
        table.add_row("warning", issue, style="yellow")
    console.print(table)

    if errors or (fail_on_warning and warnings):
        raise typer.Exit(code=1)

    console.print("[green]Dataset looks good![/green]")


if __name__ == "__main__":
    app()
