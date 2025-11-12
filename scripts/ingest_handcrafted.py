"""Ingest handcrafted Database Systems assets into the world-model store."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from world_model.storage import WorldModelStore  # noqa: E402

LOGGER = logging.getLogger("ingest_handcrafted")


def ingest(
    source_dir: Path,
    dest_path: Path,
    *,
    jsonl_path: Path | None = None,
) -> Dict[str, int]:
    """Hydrate the SQLite world model from handcrafted YAML/CSV assets."""

    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory {source_dir} does not exist")

    dest_path = dest_path.resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    datasets = _load_datasets(source_dir)

    # Ensure schema exists before opening our own connection.
    WorldModelStore(dest_path)

    conn = sqlite3.connect(dest_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        with conn:
            _insert_authors(conn, datasets["authors"])
            _insert_papers(conn, datasets["papers"], datasets["authors"])
            _insert_concepts(conn, datasets["concepts"])
            _insert_relationships(conn, datasets["concepts"])
            _insert_graph_edges(conn, datasets.get("graph_edges", []))
            _insert_claims(conn, datasets["concepts"], datasets.get("definitions", []))
            _insert_timeline(conn, datasets["timeline"], datasets["concepts"])
            _insert_artifacts(
                conn,
                quiz_items=datasets["quiz_bank"],
                course_outline=datasets.get("course_outline"),
                source_dir=source_dir,
            )
        summary = {
            "authors": len(datasets["authors"]),
            "papers": len(datasets["papers"]),
            "concepts": len(datasets["concepts"]),
            "timeline": len(datasets["timeline"]),
        }
    finally:
        conn.close()

    if jsonl_path:
        _write_snapshot(jsonl_path, datasets)

    return summary


# ---------------------------------------------------------------------------
# Loading helpers


def _load_datasets(source_dir: Path) -> Dict[str, Any]:
    authors = _load_csv(source_dir / "authors.csv")
    author_ids = {row["id"] for row in authors}

    papers = _load_csv(source_dir / "papers.csv")
    for row in papers:
        field = row.get("author_ids") or row.get("authors")
        if field is None:
            raise ValueError(f"Paper {row.get('id')} missing authors column")
        ids = [token.strip() for token in field.split(";") if token.strip()]
        missing = [aid for aid in ids if aid not in author_ids]
        if missing:
            raise ValueError(f"Paper {row['id']} references unknown authors: {missing}")
        row["author_list"] = ids

    concepts_raw = yaml.safe_load((source_dir / "concepts.yaml").read_text(encoding="utf-8")) or {}
    concepts = concepts_raw.get("concepts", {})
    if not isinstance(concepts, dict):
        raise ValueError("concepts.yaml must define a mapping under 'concepts'")

    paper_ids = {row["id"] for row in papers}
    for concept_id, payload in concepts.items():
        parent = payload.get("parent")
        if parent and parent not in concepts:
            raise ValueError(f"Concept {concept_id} references unknown parent {parent}")
        for source_id in payload.get("canonical_sources", []) or []:
            if source_id not in paper_ids:
                raise ValueError(f"Concept {concept_id} references unknown source {source_id}")

    timeline_rows = _load_csv(source_dir / "timeline.csv")
    for row in timeline_rows:
        related = _split_list(row.get("related_concepts", ""))
        row["concept_ids"] = related
        raw_citation = row.get("citation_id") or row.get("citation")
        citation_id = raw_citation.strip() if isinstance(raw_citation, str) else raw_citation
        if citation_id:
            row["citation_id"] = citation_id
        else:
            row.pop("citation_id", None)
        if citation_id and citation_id not in paper_ids:
            raise ValueError(
                f"Timeline entry {row.get('event')} references unknown citation {citation_id}"
            )
        for cid in related:
            if cid not in concepts:
                raise ValueError(
                    f"Timeline entry {row.get('event')} references unknown concept {cid}"
                )

    quiz_bank = json.loads((source_dir / "quiz_bank.json").read_text(encoding="utf-8"))
    for quiz in quiz_bank:
        for objective in quiz.get("learning_objectives", []):
            if objective not in concepts:
                raise ValueError(f"Quiz item {quiz['id']} references unknown concept {objective}")


    graph_path = source_dir / "graph.yaml"
    graph = yaml.safe_load(graph_path.read_text(encoding="utf-8")) if graph_path.exists() else {}

    definitions_path = source_dir / "definitions.yaml"
    definitions_data = (
        yaml.safe_load(definitions_path.read_text(encoding="utf-8"))
        if definitions_path.exists()
        else {}
    )
    definitions_list = (
        definitions_data.get("definitions", []) if isinstance(definitions_data, dict) else []
    )
    for entry in definitions_list:
        concept_ref = entry.get("concept")
        if concept_ref not in concepts:
            raise ValueError(
                f"Definition {entry.get('id')} references unknown concept {concept_ref}"
            )
        citation_ref = entry.get("citation")
        if citation_ref and citation_ref not in paper_ids:
            raise ValueError(
                f"Definition {entry.get('id')} references unknown citation {citation_ref}"
            )

    edge_list = graph.get("edges", []) if isinstance(graph, dict) else []
    for edge in edge_list:
        for field in ("source", "target"):
            cid = edge.get(field)
            if cid not in concepts:
                raise ValueError(f"Graph edge references unknown concept {cid}")
        for citation_id in edge.get("citations", []) or []:
            if citation_id not in paper_ids:
                raise ValueError(
                    "Graph edge ("
                    f"{edge.get('source')} -> {edge.get('target')}) "
                    f"cites unknown paper {citation_id}"
                )

    citations_path = source_dir / "citations.yaml"
    citations = (
        yaml.safe_load(citations_path.read_text(encoding="utf-8"))
        if citations_path.exists()
        else {}
    )

    taxonomy_path = source_dir / "taxonomy.yaml"
    taxonomy = (
        yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
        if taxonomy_path.exists()
        else {}
    )

    course_outline_path = source_dir / "course_outline.yaml"
    course_outline = (
        yaml.safe_load(course_outline_path.read_text(encoding="utf-8"))
        if course_outline_path.exists()
        else {}
    )

    return {
        "authors": authors,
        "papers": papers,
        "concepts": concepts,
        "timeline": timeline_rows,
        "quiz_bank": quiz_bank,
        "citations": citations,
        "taxonomy": taxonomy,
        "course_outline": course_outline,
        "graph_edges": edge_list,
        "definitions": definitions_list,
    }


def _load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Expected CSV at {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, str]] = []
        for row in reader:
            cleaned = {
                key: (value.strip() if isinstance(value, str) else value)
                for key, value in row.items()
            }
            has_value = False
            for value in cleaned.values():
                if isinstance(value, str) and value.strip():
                    has_value = True
                    break
                if value not in (None, ""):
                    has_value = True
                    break
            if has_value:
                rows.append(cleaned)
        return rows


def _split_list(raw: str) -> List[str]:
    return [token.strip() for token in (raw or "").split(";") if token.strip()]


# ---------------------------------------------------------------------------
# Insert helpers


def _insert_authors(conn: sqlite3.Connection, authors: List[Dict[str, str]]) -> None:
    rows = [(row["id"], row.get("full_name"), row.get("affiliation")) for row in authors]
    conn.executemany(
        "INSERT INTO authors (id, full_name, affiliation) VALUES (?, ?, ?)",
        rows,
    )
    LOGGER.info("Inserted %d authors", len(rows))


def _insert_papers(
    conn: sqlite3.Connection,
    papers: List[Dict[str, str]],
    authors: List[Dict[str, str]],
) -> None:
    author_lookup = {row["id"]: row for row in authors}
    paper_rows = []
    mapping_rows = []
    for row in papers:
        paper_rows.append(
            (
                row["id"],
                row.get("title"),
                row.get("venue"),
                int(row.get("year")) if row.get("year") else None,
                row.get("url"),
            )
        )
        for position, author_id in enumerate(row.get("author_list", []), start=1):
            if author_id not in author_lookup:
                raise ValueError(f"Unknown author {author_id} for paper {row['id']}")
            mapping_rows.append((row["id"], author_id, position))
    conn.executemany(
        "INSERT INTO papers (id, title, venue, year, url) VALUES (?, ?, ?, ?, ?)",
        paper_rows,
    )
    if mapping_rows:
        conn.executemany(
            "INSERT INTO paper_authors (paper_id, author_id, position) VALUES (?, ?, ?)",
            mapping_rows,
        )
    LOGGER.info("Inserted %d papers", len(paper_rows))


def _order_concepts(concepts: Dict[str, Dict[str, Any]]) -> List[tuple[str, Dict[str, Any]]]:
    remaining = OrderedDict(concepts)
    ordered: List[tuple[str, Dict[str, Any]]] = []
    resolved: set[str] = set()
    while remaining:
        progress = False
        for concept_id, payload in list(remaining.items()):
            parent = payload.get("parent")
            if parent and parent in concepts and parent not in resolved:
                continue
            ordered.append((concept_id, payload))
            resolved.add(concept_id)
            del remaining[concept_id]
            progress = True
        if not progress:
            raise ValueError("Cycle detected in concept parents; check concepts.yaml")
    return ordered


def _insert_concepts(conn: sqlite3.Connection, concepts: Dict[str, Dict[str, Any]]) -> None:
    ordered = _order_concepts(concepts)
    rows = [
        (
            concept_id,
            payload.get("name"),
            payload.get("summary"),
            payload.get("parent"),
        )
        for concept_id, payload in ordered
    ]
    conn.executemany(
        "INSERT INTO concepts (id, name, summary, parent_id) VALUES (?, ?, ?, ?)",
        rows,
    )
    LOGGER.info("Inserted %d concepts", len(rows))


def _insert_relationships(conn: sqlite3.Connection, concepts: Dict[str, Dict[str, Any]]) -> None:
    relations: List[tuple[str, str, str, str]] = []
    for concept_id, payload in concepts.items():
        parent = payload.get("parent")
        if parent:
            relations.append(
                (concept_id, parent, "is_part_of", "Declared parent-child relationship")
            )
        for prereq in payload.get("prerequisites", []) or []:
            if prereq not in concepts:
                raise ValueError(f"Concept {concept_id} lists unknown prerequisite {prereq}")
            relations.append((prereq, concept_id, "prerequisite", "Concept prerequisite graph"))
    if relations:
        conn.executemany(
            "INSERT INTO relationships (source_id, target_id, relation_type, justification) "
            "VALUES (?, ?, ?, ?)",
            relations,
        )
    LOGGER.info("Inserted %d relationships", len(relations))


def _insert_claims(
    conn: sqlite3.Connection,
    concepts: Dict[str, Dict[str, Any]],
    definitions: List[Dict[str, Any]],
) -> None:
    claim_rows = []
    for concept_id, payload in concepts.items():
        summary = payload.get("summary")
        if not summary:
            continue
        sources = payload.get("canonical_sources", []) or []
        primary = sources[0] if sources else None
        provenance = json.dumps({"sources": sources})
        claim_rows.append((concept_id, summary, primary, "concept_summary", provenance))
    for definition in definitions:
        concept_ref = definition.get("concept")
        statement = definition.get("statement")
        if not concept_ref or not statement:
            continue
        provenance = json.dumps(
            {
                "definition_id": definition.get("id"),
                "source_excerpt": definition.get("source_excerpt"),
            },
            ensure_ascii=False,
        )
        claim_rows.append(
            (
                concept_ref,
                statement,
                definition.get("citation"),
                "definition",
                provenance,
            )
        )
    if claim_rows:
        conn.executemany(
            "INSERT INTO claims (subject_id, body, citation, created_by, provenance) "
            "VALUES (?, ?, ?, ?, ?)",
            claim_rows,
        )
    LOGGER.info("Inserted %d claims", len(claim_rows))


def _insert_graph_edges(conn: sqlite3.Connection, edges: List[Dict[str, Any]]) -> None:
    if not edges:
        return
    rows = []
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        relation_type = edge.get("relation") or edge.get("relation_type") or "related_to"
        description = edge.get("description") or ""
        citations = edge.get("citations") or []
        if citations:
            refs = ", ".join(citations)
            description = f"{description} (sources: {refs})" if description else f"sources: {refs}"
        if not source or not target:
            continue
        rows.append((source, target, relation_type, description))
    if rows:
        conn.executemany(
            "INSERT INTO relationships (source_id, target_id, relation_type, justification) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )
        LOGGER.info("Inserted %d graph edges", len(rows))


def _insert_timeline(
    conn: sqlite3.Connection,
    events: List[Dict[str, Any]],
    concepts: Dict[str, Dict[str, Any]],
) -> None:
    rows: List[tuple[int | None, str, str, str, str | None]] = []
    for row in events:
        year = int(row["year"]) if row.get("year") else None
        description = row.get("why_it_matters")
        event_label = row.get("event")
        citation = row.get("citation_id") or row.get("citation")
        for concept_id in row.get("concept_ids", []):
            if concept_id not in concepts:
                raise ValueError(f"Timeline references unknown concept {concept_id}")
            rows.append((year, event_label, description, concept_id, citation))
    if rows:
        conn.executemany(
            "INSERT INTO observations (event_year, event_label, summary, "
            "related_concept, citation) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    LOGGER.info("Inserted %d timeline observations", len(rows))


def _insert_artifacts(
    conn: sqlite3.Connection,
    quiz_items: List[Dict[str, Any]],
    course_outline: Dict[str, Any] | None,
    source_dir: Path,
) -> None:
    rows: List[tuple[str, str, str]] = []
    if quiz_items:
        rows.append(
            (
                "quiz_bank",
                str((source_dir / "quiz_bank.json").resolve()),
                json.dumps({"count": len(quiz_items), "items": quiz_items}, ensure_ascii=False),
            )
        )
    if course_outline:
        rows.append(
            (
                "course_outline",
                str((source_dir / "course_outline.yaml").resolve()),
                json.dumps(course_outline, ensure_ascii=False),
            )
        )
    if rows:
        conn.executemany(
            "INSERT INTO artifacts (artifact_type, uri, metadata) VALUES (?, ?, ?)",
            rows,
        )
        LOGGER.info("Inserted %d artifacts", len(rows))


# ---------------------------------------------------------------------------
# Snapshot export


def _write_snapshot(jsonl_path: Path, datasets: Dict[str, Any]) -> None:
    jsonl_path = jsonl_path.resolve()
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []

    for concept_id, payload in datasets["concepts"].items():
        records.append(
            {
                "type": "concept",
                "id": concept_id,
                "name": payload.get("name"),
                "summary": payload.get("summary"),
                "parent": payload.get("parent"),
                "prerequisites": payload.get("prerequisites", []),
                "canonical_sources": payload.get("canonical_sources", []),
            }
        )

    for paper in datasets["papers"]:
        records.append(
            {
                "type": "paper",
                "id": paper.get("id"),
                "title": paper.get("title"),
                "venue": paper.get("venue"),
                "year": paper.get("year"),
                "authors": paper.get("author_list", []),
            }
        )

    for event in datasets["timeline"]:
        records.append(
            {
                "type": "timeline_event",
                "year": event.get("year"),
                "event": event.get("event"),
                "related_concepts": event.get("concept_ids", []),
                "citation_id": event.get("citation_id") or event.get("citation"),
            }
        )

    for quiz in datasets["quiz_bank"]:
        record = dict(quiz)
        record["type"] = "quiz_item"
        records.append(record)

    course_outline = datasets.get("course_outline") or {}
    if course_outline:
        outline_record = {"type": "course_outline", **course_outline}
        records.append(outline_record)

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    LOGGER.info("Wrote %d snapshot records to %s", len(records), jsonl_path)


# ---------------------------------------------------------------------------
# CLI


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest handcrafted Database Systems assets")
    parser.add_argument("source", type=Path, help="Path to data/handcrafted/database_systems")
    parser.add_argument(
        "dest",
        type=Path,
        help="Destination SQLite file (e.g., outputs/world_model/state.sqlite)",
    )
    parser.add_argument("--jsonl", type=Path, help="Optional path to write a JSONL snapshot")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    summary = ingest(args.source, args.dest, jsonl_path=args.jsonl)
    LOGGER.info("Ingestion summary: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
