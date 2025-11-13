"""Data-related helper tools surfaced to CodeAct."""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import duckdb
import yaml

logger = logging.getLogger("coursegen.codeact.data")

DATASET_ENV_VAR = "COURSEGEN_DATASET_DIR"
REPO_ENV_VAR = "COURSEGEN_REPO_ROOT"
_DATASET_SUBPATH = Path("data/handcrafted/database_systems")
_FALLBACK_DATA_ROOT = Path(__file__).resolve().parents[3] / _DATASET_SUBPATH
DATA_ROOT = _FALLBACK_DATA_ROOT  # preserved for backward compatibility
_READ_ONLY_PREFIXES = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "attach",
    "pragma",
    "copy",
    "load",
    "call",
    "install",
    "set",
}

# Tables backed by raw handcrafted assets that DuckDB can load directly.
_TABLE_SOURCES: Dict[str, Tuple[str, str]] = {
    "authors": ("csv", "authors.csv"),
    "papers": ("csv", "papers.csv"),
    "timeline": ("csv", "timeline.csv"),
    "quiz_bank": ("json", "quiz_bank.json"),
}


def _default_dataset_dir() -> Path:
    env_override = os.getenv(DATASET_ENV_VAR)
    if env_override:
        return Path(env_override)
    repo_root = os.getenv(REPO_ENV_VAR)
    if repo_root:
        return Path(repo_root).expanduser().resolve() / _DATASET_SUBPATH
    return _FALLBACK_DATA_ROOT


def get_dataset_root() -> Path:
    """Return the currently configured dataset root."""

    return _default_dataset_dir().expanduser().resolve()


def load_dataset_asset(name: str, base_dir: Path | None = None) -> dict[str, Any]:
    """Return the contents of a JSON/YAML dataset asset."""

    base = _resolve_dataset_dir(base_dir)
    asset_path = base / name
    if not asset_path.exists():
        logger.warning("Dataset asset %s not found, returning stub payload", asset_path)
        return {"asset": name, "entries": []}

    text = asset_path.read_text(encoding="utf-8")
    suffix = asset_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            data = yaml.safe_load(text) or {}
            if isinstance(data, dict):
                return data
            return {"asset": name, "data": data}
        except yaml.YAMLError as exc:  # noqa: PERF203 - informative log
            logger.warning("Failed to parse YAML asset %s: %s", asset_path, exc)
            return {"asset": name, "content": text}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Asset %s is not JSON/YAML; returning raw text", asset_path)
        return {"asset": name, "content": text}


def run_sql_query(query: str, *, dataset_dir: Path | None = None) -> list[dict[str, Any]]:
    """Execute read-only SQL queries against the handcrafted dataset via DuckDB.

    Parameters
    ----------
    query:
        SQL query that references the registered tables (authors, papers, timeline,
        quiz_bank). Only single-statement queries are supported.
    dataset_dir:
        Optional override for the dataset root, primarily for tests.
    """

    normalized = (query or "").strip()
    if not normalized:
        raise ValueError("run_sql_query received an empty query")
    if _is_mutating_statement(normalized):
        raise ValueError("run_sql_query only accepts read-only SELECT/CTE statements")

    dataset_dir = _resolve_dataset_dir(dataset_dir)
    logger.debug("run_sql_query dir=%s sql=%s", dataset_dir, normalized)
    conn = duckdb.connect(database=":memory:")
    try:
        _register_dataset_tables(conn, dataset_dir)
        logger.debug("Executing DuckDB query: %s", normalized)
        cursor = conn.execute(normalized)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except duckdb.Error as exc:  # pragma: no cover - exercised via tests
        raise ValueError(f"DuckDB failed to execute query: {exc}") from exc
    finally:
        conn.close()


def _resolve_dataset_dir(dataset_dir: Path | None) -> Path:
    base_candidate: Path
    if dataset_dir is None:
        base_candidate = _default_dataset_dir()
    else:
        base_candidate = Path(dataset_dir)
    base = base_candidate.expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(f"Dataset directory not found: {base}")
    return base


def _register_dataset_tables(conn: duckdb.DuckDBPyConnection, dataset_dir: Path) -> None:
    for table_name, (fmt, relative_path) in _TABLE_SOURCES.items():
        asset_path = dataset_dir / relative_path
        if not asset_path.exists():
            logger.warning("Dataset asset %s missing; skipping table %s", asset_path, table_name)
            continue
        escaped = str(asset_path).replace("'", "''")
        if fmt == "csv":
            conn.execute(
                f"CREATE OR REPLACE TEMP VIEW \"{table_name}\" AS "
                f"SELECT * FROM read_csv_auto('{escaped}', HEADER=TRUE)"
            )
        elif fmt == "json":
            conn.execute(
                f"CREATE OR REPLACE TEMP VIEW \"{table_name}\" AS "
                f"SELECT * FROM read_json_auto('{escaped}')"
            )
        else:
            logger.warning("Unsupported dataset format %s for table %s", fmt, table_name)
    _register_concepts_table(conn, dataset_dir / "concepts.yaml")
    _register_domains_table(conn, dataset_dir / "taxonomy.yaml")
    _register_definitions_table(conn, dataset_dir / "definitions.yaml")
    _register_graph_table(conn, dataset_dir / "graph.yaml")


def _register_concepts_table(conn: duckdb.DuckDBPyConnection, concepts_path: Path) -> None:
    rows = _load_concept_rows(concepts_path)
    if not rows:
        logger.warning("Concepts asset missing or empty: %s", concepts_path)
        return
    conn.execute(
        """
        CREATE OR REPLACE TEMP TABLE concepts (
            id TEXT,
            name TEXT,
            summary TEXT,
            parent_id TEXT,
            prerequisites JSON,
            canonical_sources JSON
        )
        """
    )
    conn.executemany("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?)", rows)


def _register_domains_table(conn: duckdb.DuckDBPyConnection, taxonomy_path: Path) -> None:
    rows = _load_domain_rows(taxonomy_path)
    if not rows:
        return
    conn.execute(
        """
        CREATE OR REPLACE TEMP TABLE domains (
            id TEXT,
            title TEXT,
            summary TEXT,
            focus TEXT,
            concept_ids JSON
        )
        """
    )
    conn.executemany("INSERT INTO domains VALUES (?, ?, ?, ?, ?)", rows)


def _register_definitions_table(conn: duckdb.DuckDBPyConnection, definitions_path: Path) -> None:
    rows = _load_definition_rows(definitions_path)
    if not rows:
        return
    conn.execute(
        """
        CREATE OR REPLACE TEMP TABLE definitions (
            id TEXT,
            concept_id TEXT,
            statement TEXT,
            citation TEXT,
            source_excerpt TEXT
        )
        """
    )
    conn.executemany("INSERT INTO definitions VALUES (?, ?, ?, ?, ?)", rows)


def _register_graph_table(conn: duckdb.DuckDBPyConnection, graph_path: Path) -> None:
    rows = _load_graph_rows(graph_path)
    if not rows:
        return
    conn.execute(
        """
        CREATE OR REPLACE TEMP TABLE graph_edges (
            source_id TEXT,
            target_id TEXT,
            relation_type TEXT,
            description TEXT,
            citations JSON
        )
        """
    )
    conn.executemany("INSERT INTO graph_edges VALUES (?, ?, ?, ?, ?)", rows)


def _load_concept_rows(path: Path) -> List[tuple[str, str | None, str | None, str | None, str, str]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    concepts = data.get("concepts", {}) if isinstance(data, dict) else {}
    rows: List[tuple[str, str | None, str | None, str | None, str, str]] = []
    for concept_id, payload in concepts.items():
        rows.append(
            (
                concept_id,
                payload.get("name"),
                payload.get("summary"),
                payload.get("parent"),
                json.dumps(payload.get("prerequisites", []), ensure_ascii=False),
                json.dumps(payload.get("canonical_sources", []), ensure_ascii=False),
            )
        )
    return rows


def _load_domain_rows(path: Path) -> List[tuple[str | None, str | None, str | None, str | None, str]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    domains = data.get("domains", []) if isinstance(data, dict) else []
    rows: List[tuple[str | None, str | None, str | None, str | None, str]] = []
    for domain in domains:
        summary = domain.get("summary")
        focus = domain.get("focus")
        if summary is None:
            summary = focus
        if focus is None:
            focus = summary
        rows.append(
            (
                domain.get("id"),
                domain.get("title"),
                summary,
                focus,
                json.dumps(domain.get("concepts", []), ensure_ascii=False),
            )
        )
    return rows


def _load_definition_rows(path: Path) -> List[tuple[str | None, str | None, str | None, str | None, str | None]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("definitions", []) if isinstance(data, dict) else []
    rows: List[tuple[str | None, str | None, str | None, str | None, str | None]] = []
    for entry in entries:
        rows.append(
            (
                entry.get("id"),
                entry.get("concept"),
                entry.get("statement"),
                entry.get("citation"),
                entry.get("source_excerpt"),
            )
        )
    return rows


def _load_graph_rows(path: Path) -> List[tuple[str | None, str | None, str | None, str | None, str]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    edges = data.get("edges", []) if isinstance(data, dict) else []
    rows: List[tuple[str | None, str | None, str | None, str | None, str]] = []
    for edge in edges:
        rows.append(
            (
                edge.get("source"),
                edge.get("target"),
                edge.get("relation") or edge.get("relation_type"),
                edge.get("description"),
                json.dumps(edge.get("citations", []), ensure_ascii=False),
            )
        )
    return rows


def _is_mutating_statement(statement: str) -> bool:
    if not statement:
        return False

    sanitized = _strip_literals_and_comments(statement)
    cleaned = sanitized.strip().lower()
    if not cleaned:
        return False

    segments = [segment.strip() for segment in cleaned.split(";") if segment.strip()]
    if len(segments) > 1:
        return True  # multi-statement payloads are not allowed

    tokens = re.findall(r"\b[a-z_]+\b", segments[0])
    return any(token in _READ_ONLY_PREFIXES for token in tokens)


def _strip_literals_and_comments(sql: str) -> str:
    """Remove string literals and comments so keyword scans stay reliable."""

    result: List[str] = []
    i = 0
    length = len(sql)
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False

    while i < length:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < length else ""

        if in_single:
            if ch == "'" and nxt == "'":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            if ch == '"' and nxt == '"':
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append("\n")
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if ch == "'":
            in_single = True
            i += 1
            continue

        if ch == '"':
            in_double = True
            i += 1
            continue

        if ch == "-" and nxt == "-":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        result.append(ch)
        i += 1

    return "".join(result)
