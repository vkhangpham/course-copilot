"""CLI helpers for inspecting the Database Systems world model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from world_model.storage import WorldModelStore

app = typer.Typer(help="Inspect concepts, timeline events, and claims in the world model.")
console = Console()


def _resolve_store(path: Path) -> WorldModelStore:
    path = path.expanduser().resolve()
    if not path.exists():
        raise typer.BadParameter(f"World model store not found at {path}")
    return WorldModelStore(path)


def query_concepts(store_path: Path, topic: Optional[str] = None) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT id, name, summary, parent_id FROM concepts"
    params: tuple = tuple()
    if topic:
        sql += " WHERE name LIKE ? OR summary LIKE ?"
        like = f"%{topic}%"
        params = (like, like)
    sql += " ORDER BY name"
    rows = store.query(sql, params)
    return [
        {
            "id": row[0],
            "name": row[1],
            "summary": row[2],
            "parent_id": row[3],
        }
        for row in rows
    ]


def query_timeline(
    store_path: Path,
    concept_id: Optional[str] = None,
    year: Optional[int] = None,
) -> List[dict]:
    store = _resolve_store(store_path)
    sql = (
        "SELECT event_year, event_label, summary, related_concept, citation FROM observations"
    )
    params: tuple = tuple()
    where_clauses = []
    if concept_id:
        where_clauses.append("related_concept = ?")
        params += (concept_id,)
    if year is not None:
        where_clauses.append("event_year = ?")
        params += (year,)
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY event_year"
    rows = store.query(sql, params)
    return [
        {
            "year": row[0],
            "event": row[1],
            "summary": row[2],
            "concept": row[3],
            "citation": row[4],
        }
        for row in rows
    ]


def query_claims(store_path: Path, concept_id: str) -> List[dict]:
    store = _resolve_store(store_path)
    sql = (
        "SELECT subject_id, body, citation, created_at FROM claims WHERE subject_id = ? ORDER BY created_at DESC"
    )
    rows = store.query(sql, (concept_id,))
    return [
        {
            "concept": row[0],
            "body": row[1],
            "citation": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]


def query_papers(
    store_path: Path,
    keyword: Optional[str] = None,
    year: Optional[int] = None,
) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT id, title, venue, year FROM papers"
    params: tuple = tuple()
    clauses = []
    if keyword:
        clauses.append("(LOWER(title) LIKE ? OR LOWER(venue) LIKE ?)")
        like = f"%{keyword.lower()}%"
        params += (like, like)
    if year is not None:
        clauses.append("year = ?")
        params += (year,)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY year, title"
    rows = store.query(sql, params)
    return [
        {"id": row[0], "title": row[1], "venue": row[2], "year": row[3]}
        for row in rows
    ]


def query_authors(store_path: Path, keyword: Optional[str] = None) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT id, full_name, affiliation FROM authors"
    params: tuple = tuple()
    if keyword:
        sql += " WHERE LOWER(full_name) LIKE ?"
        params = (f"%{keyword.lower()}%",)
    sql += " ORDER BY full_name"
    rows = store.query(sql, params)
    return [
        {"id": row[0], "name": row[1], "affiliation": row[2]}
        for row in rows
    ]


def _print_table(headers: list[str], rows: List[dict], keys: list[str]) -> None:
    table = Table(*headers)
    for row in rows:
        table.add_row(*[str(row.get(key, "")) for key in keys])
    console.print(table)


@app.command()
def concepts(
    store: Path = typer.Option(Path("world_model/state.sqlite"), "--store", help="SQLite world model path"),
    topic: Optional[str] = typer.Option(None, help="Case-insensitive substring to filter names/summaries."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List concepts in the world model."""

    rows = query_concepts(store, topic)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    _print_table(["ID", "Name", "Parent"], rows, ["id", "name", "parent_id"])


@app.command()
def timeline(
    store: Path = typer.Option(Path("world_model/state.sqlite"), "--store"),
    concept: Optional[str] = typer.Option(None, help="Filter by related concept id."),
    year: Optional[int] = typer.Option(None, help="Filter by event year."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show timeline events (optionally filtered by concept)."""

    rows = query_timeline(store, concept, year)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    _print_table(["Year", "Event", "Concept", "Citation"], rows, ["year", "event", "concept", "citation"])


@app.command()
def claims(
    concept: str = typer.Argument(..., help="Concept identifier (see concepts command)."),
    store: Path = typer.Option(Path("world_model/state.sqlite"), "--store"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show definition/provenance claims for a concept."""

    rows = query_claims(store, concept)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print(f"[yellow]No claims stored for {concept}[/yellow]")
        return
    _print_table(["Concept", "Claim", "Citation"], rows, ["concept", "body", "citation"])


@app.command()
def papers(
    store: Path = typer.Option(Path("world_model/state.sqlite"), "--store"),
    keyword: Optional[str] = typer.Option(None, help="Case-insensitive match on title or venue."),
    year: Optional[int] = typer.Option(None, help="Filter by publication year."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List papers available in the world model."""

    rows = query_papers(store, keyword, year)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print("[yellow]No matching papers found.[/yellow]")
        return
    _print_table(["ID", "Title", "Venue", "Year"], rows, ["id", "title", "venue", "year"])


@app.command()
def authors(
    store: Path = typer.Option(Path("world_model/state.sqlite"), "--store"),
    keyword: Optional[str] = typer.Option(None, help="Case-insensitive substring match."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List authors captured in the world model."""

    rows = query_authors(store, keyword)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print("[yellow]No matching authors found.[/yellow]")
        return
    _print_table(["ID", "Name", "Affiliation"], rows, ["id", "name", "affiliation"])


if __name__ == "__main__":  # pragma: no cover
    app()
