from pathlib import Path

import pytest

from scripts.ingest_handcrafted import ingest
from scripts.query_world_model import (
    query_authors,
    query_claims,
    query_concepts,
    query_papers,
    query_timeline,
)

DATASET = Path(__file__).resolve().parents[1] / "data" / "handcrafted" / "database_systems"


def _build_store(tmp_path: Path) -> Path:
    store = tmp_path / "state.sqlite"
    ingest(DATASET, store)
    return store


def test_query_concepts_filters_by_topic(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_concepts(store, topic="transaction")
    assert any("Transaction" in row["name"] for row in rows)


def test_query_timeline_filters_by_concept_and_year(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    concept_id = "relational_model"
    rows = query_timeline(store, concept_id, year=1970)
    assert rows, "Expected timeline rows for relational_model"
    assert all(row["concept"] == concept_id for row in rows)
    assert all(row["year"] == 1970 for row in rows)


def test_query_claims_returns_definitions(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_claims(store, "relational_model")
    assert rows, "Relational model should have at least one stored claim"
    first = rows[0]
    assert first["concept"] == "relational_model"
    assert first["citation"]


def test_query_claims_handles_missing_concept(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_claims(store, "nonexistent_concept")
    assert rows == []


def test_query_papers_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_papers(store, keyword="relational")
    assert rows, "Expected at least one relational paper"
    assert all("relational" in row["title"].lower() for row in rows)


def test_query_authors_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_authors(store, keyword="stonebraker")
    assert rows == [
        {
            "id": "stonebraker",
            "name": "Michael Stonebraker",
            "affiliation": "UC Berkeley",
        }
    ]
