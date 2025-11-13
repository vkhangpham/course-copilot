"""CLI helpers for inspecting the Database Systems world model."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from world_model.storage import WorldModelStore

ENV_REPO_ROOT = "COURSEGEN_REPO_ROOT"
STORE_ENV_VAR = "WORLD_MODEL_STORE"


def _resolve_repo_root() -> Path:
    override = os.environ.get(ENV_REPO_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def _resolve_default_store(repo_root: Path | None = None) -> Path:
    env_store = os.environ.get(STORE_ENV_VAR)
    if env_store:
        return Path(env_store).expanduser().resolve()
    base_root = repo_root or _resolve_repo_root()
    return (base_root / "outputs" / "world_model" / "state.sqlite").resolve()


REPO_ROOT = _resolve_repo_root()
DEFAULT_STORE = _resolve_default_store(REPO_ROOT)

app = typer.Typer(help="Inspect concepts, timeline events, and claims in the world model.")
console = Console()


def _resolve_store(path: Path | None) -> WorldModelStore:
    resolved = (
        path.expanduser().resolve()
        if path is not None
        else _resolve_default_store()
    )
    if not resolved.exists():
        raise typer.BadParameter(f"World model store not found at {resolved}")
    return WorldModelStore(resolved)


def query_concepts(store_path: Path | None = None, topic: Optional[str] = None) -> List[dict]:
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
    store_path: Path | None = None,
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


def query_claims(
    store_path: Path | None = None,
    concept_id: Optional[str] = None,
    limit: int = 25,
) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT subject_id, body, citation, confidence, asserted_at, created_at FROM claims"
    params: List[Any] = []
    if concept_id:
        sql += " WHERE subject_id = ?"
        params.append(concept_id)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = store.query(sql, tuple(params))
    return [
        {
            "concept": row[0],
            "body": row[1],
            "citation": row[2],
            "confidence": row[3],
            "asserted_at": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def query_papers(
    store_path: Path | None = None,
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


def query_authors(store_path: Path | None = None, keyword: Optional[str] = None) -> List[dict]:
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


def query_artifacts(store_path: Path | None = None, artifact_type: Optional[str] = None) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT artifact_type, uri, metadata, created_at FROM artifacts"
    params: tuple = tuple()
    if artifact_type:
        sql += " WHERE artifact_type = ?"
        params = (artifact_type,)
    sql += " ORDER BY created_at DESC"
    rows = store.query(sql, params)
    return [
        {
            "type": row[0],
            "uri": row[1],
            "metadata": _safe_json(row[2]),
            "created_at": row[3],
        }
        for row in rows
    ]


def query_definitions(store_path: Path | None = None, concept_id: Optional[str] = None) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT subject_id, body, citation, provenance FROM claims WHERE created_by = 'definition'"
    params: tuple = tuple()
    if concept_id:
        sql += " AND subject_id = ?"
        params = (concept_id,)
    sql += " ORDER BY subject_id"
    rows = store.query(sql, params)
    return [
        {
            "concept": row[0],
            "text": row[1],
            "citation": row[2],
            "source_excerpt": _extract_excerpt(row[3]),
        }
        for row in rows
    ]


def query_graph_edges(store_path: Path | None = None, concept_id: Optional[str] = None) -> List[dict]:
    store = _resolve_store(store_path)
    sql = "SELECT source_id, target_id, relation_type, justification FROM relationships"
    params: tuple = tuple()
    if concept_id:
        sql += " WHERE source_id = ? OR target_id = ?"
        params = (concept_id, concept_id)
    sql += " ORDER BY source_id, target_id"
    rows = store.query(sql, params)
    return [
        {
            "source": row[0],
            "target": row[1],
            "relation": row[2],
            "justification": row[3],
        }
        for row in rows
    ]


def _print_table(headers: list[str], rows: List[dict], keys: list[str]) -> None:
    table = Table(*headers)
    for row in rows:
        table.add_row(*[str(row.get(key, "")) for key in keys])
    console.print(table)


def _count_rows(store: WorldModelStore, sql: str, params: tuple | None = None) -> int:
    rows = store.query(sql, params or tuple())
    if not rows:
        return 0
    value = rows[0][0]
    return int(value) if value is not None else 0


def _summarize_artifact_metadata(rows: List[tuple]) -> Dict[str, Dict[str, Any]]:
    details: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not row:
            continue
        artifact_type = str(row[0]) if row[0] is not None else "unknown"
        metadata = _safe_json(row[1])
        entry: Dict[str, Any] = {}
        if artifact_type == "quiz_bank" and isinstance(metadata, dict):
            count = metadata.get("count")
            if count is None and isinstance(metadata.get("items"), list):
                count = len(metadata["items"])
            if count is not None:
                entry["questions"] = int(count)
        elif artifact_type == "course_outline" and isinstance(metadata, dict):
            weeks = metadata.get("weeks")
            if isinstance(weeks, list):
                entry["weeks"] = len(weeks)
        if entry:
            details[artifact_type] = entry
    return details


def query_summary(store_path: Path | None = None) -> Dict[str, Any]:
    store = _resolve_store(store_path)

    counts = {
        "concepts": _count_rows(store, "SELECT COUNT(*) FROM concepts"),
        "relationships": _count_rows(store, "SELECT COUNT(*) FROM relationships"),
        "authors": _count_rows(store, "SELECT COUNT(*) FROM authors"),
        "papers": _count_rows(store, "SELECT COUNT(*) FROM papers"),
        "timeline_events": _count_rows(store, "SELECT COUNT(*) FROM observations"),
        "claims": _count_rows(store, "SELECT COUNT(*) FROM claims"),
        "definitions": _count_rows(
            store, "SELECT COUNT(*) FROM claims WHERE created_by = ?", ("definition",)
        ),
    }

    artifact_rows = store.query(
        "SELECT artifact_type, COUNT(*) FROM artifacts GROUP BY artifact_type ORDER BY artifact_type"
    )
    artifact_counts = {
        str(row[0]): int(row[1]) for row in artifact_rows if row and row[0] is not None
    }
    artifact_detail_rows = store.query("SELECT artifact_type, metadata FROM artifacts")
    artifact_details = _summarize_artifact_metadata(artifact_detail_rows)
    counts["artifacts"] = sum(artifact_counts.values())

    last_artifact_row = store.query("SELECT MAX(created_at) FROM artifacts")
    last_artifact_at = last_artifact_row[0][0] if last_artifact_row else None

    return {
        "store": str(store.db_path),
        "exists": Path(store.db_path).exists(),
        "counts": counts,
        "artifacts_by_type": artifact_counts,
        "artifact_details": artifact_details,
        "last_artifact_at": last_artifact_at,
    }


def _print_summary(summary: Dict[str, Any]) -> None:
    console.print(f"[bold]World model store:[/bold] {summary.get('store')}")
    counts = summary.get("counts", {})
    table = Table("Metric", "Count")
    for label, key in (
        ("Concepts", "concepts"),
        ("Relationships", "relationships"),
        ("Authors", "authors"),
        ("Papers", "papers"),
        ("Timeline events", "timeline_events"),
        ("Claims", "claims"),
        ("Definitions", "definitions"),
        ("Artifacts", "artifacts"),
    ):
        value = counts.get(key)
        if value is None:
            continue
        table.add_row(label, str(value))
    console.print(table)

    artifact_counts = summary.get("artifacts_by_type", {})
    if artifact_counts:
        artifact_table = Table("Artifact type", "Count")
        for artifact_type, count in artifact_counts.items():
            artifact_table.add_row(artifact_type, str(count))
        console.print(artifact_table)

    artifact_details = summary.get("artifact_details", {})
    if artifact_details:
        detail_table = Table("Artifact", "Details")
        for artifact_type, info in artifact_details.items():
            detail_parts = [f"{key}={value}" for key, value in info.items()]
            detail_table.add_row(artifact_type, ", ".join(detail_parts))
        console.print(detail_table)

    last_artifact = summary.get("last_artifact_at")
    if last_artifact:
        console.print(f"[dim]Last artifact created at {last_artifact}[/dim]")


def _extract_excerpt(raw: object) -> str | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):  # pragma: no cover - defensive
        return None
    if isinstance(payload, dict):
        excerpt = payload.get("source_excerpt") or payload.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            return excerpt.strip()
    return None


def _safe_json(raw: object) -> dict | list | str | None:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            return raw
    return raw


@app.command()
def summary(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help=f"SQLite world model path (defaults to WORLD_MODEL_STORE or {DEFAULT_STORE}).",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Summarize the snapshot with row counts and artifact breakdown."""

    payload = query_summary(store)
    if as_json:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    _print_summary(payload)


@app.command()
def concepts(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help=f"SQLite world model path (defaults to WORLD_MODEL_STORE or {DEFAULT_STORE}).",
    ),
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
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
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
    concept: Optional[str] = typer.Argument(
        None,
        help="Concept identifier to filter by (omit to show all claims).",
    ),
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
    limit: int = typer.Option(25, min=1, help="Maximum number of rows to display."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show claims recorded in the world model."""

    rows = query_claims(store, concept, limit)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        if concept:
            console.print(f"[yellow]No claims stored for {concept}[/yellow]")
        else:
            console.print("[yellow]No claims found in the store.[/yellow]")
        return
    _print_table(["Concept", "Claim", "Citation"], rows, ["concept", "body", "citation"])


@app.command()
def papers(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
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
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
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


@app.command(name="definitions")
def definitions_command(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
    concept: Optional[str] = typer.Option(None, help="Filter by concept id."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List stored definitions for one or all concepts."""

    rows = query_definitions(store, concept)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print("[yellow]No definitions found.[/yellow]")
        return
    _print_table(["Concept", "Definition", "Citation"], rows, ["concept", "text", "citation"])


@app.command(name="graph")
def graph_command(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
    concept: Optional[str] = typer.Option(None, help="Filter edges touching this concept."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show concept relationships stored in the graph."""

    rows = query_graph_edges(store, concept)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print("[yellow]No relationships found.[/yellow]")
        return
    _print_table(["Source", "Relation", "Target"], rows, ["source", "relation", "target"])


@app.command(name="artifacts")
def artifacts_command(
    store: Path | None = typer.Option(
        None,
        "--store",
        show_default=False,
        help="Override the SQLite world model path (defaults to WORLD_MODEL_STORE or the repo outputs snapshot).",
    ),
    artifact_type: Optional[str] = typer.Option(None, "--type", help="Filter by artifact type."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List stored artifacts (quiz bank, course outline, etc.)."""

    rows = query_artifacts(store, artifact_type)
    if as_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        console.print("[yellow]No artifacts found.[/yellow]")
        return
    table = Table("Type", "URI", "Details")
    for row in rows:
        metadata = row.get("metadata")
        if isinstance(metadata, dict):
            if "count" in metadata:
                detail = f"count={metadata['count']}"
            elif "weeks" in metadata:
                detail = f"weeks={len(metadata['weeks'])}"
            else:
                detail = json.dumps(metadata, ensure_ascii=False)
        else:
            detail = str(metadata or "")
        table.add_row(str(row.get("type")), str(row.get("uri")), detail)
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
