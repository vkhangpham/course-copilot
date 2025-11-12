from pathlib import Path
import sqlite3

from apps.codeact.tools.world_model import (
    fetch_concepts,
    lookup_paper,
    record_claim,
    search_events,
)
from scripts.ingest_handcrafted import ingest

DATASET = Path(__file__).resolve().parents[1] / "data" / "handcrafted" / "database_systems"


def _build_store(tmp_path: Path) -> Path:
    store = tmp_path / "state.sqlite"
    ingest(DATASET, store)
    return store


def test_fetch_concepts_returns_tree(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = fetch_concepts(topic="transaction", depth=2, store_path=store)
    assert rows, "Expected concepts matching 'transaction'"
    assert any(entry["id"] == "transaction_management" for entry in rows)
    assert all("depth" in entry for entry in rows)


def test_search_events_filters_by_concept(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = search_events(concept_id="relational_model", store_path=store)
    assert rows, "Timeline entries should exist for relational_model"
    assert all(row["concept_id"] == "relational_model" for row in rows)


def test_lookup_paper_returns_authors(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    paper = lookup_paper("spanner-2012", store_path=store)
    assert paper["title"].startswith("Spanner")
    assert paper["authors"], "Expected author metadata"


def test_record_claim_persists(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = record_claim(
        subject="relational_model",
        content="Test harness claim",
        citation=None,
        store_path=store,
    )
    assert result["id"] >= 0
    with sqlite3.connect(store) as con:
        rows = con.execute(
            "SELECT body FROM claims WHERE subject_id = ? AND body = ?",
            ("relational_model", "Test harness claim"),
        ).fetchall()
    assert rows, "Record claim should insert into the claims table"
