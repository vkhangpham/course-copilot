import tempfile
from pathlib import Path

from scripts.ingest_handcrafted import ingest
from apps.codeact.tools.world_model import fetch_concepts, search_events, lookup_paper, record_claim
from world_model.storage import WorldModelStore

# The tests expect the world-model SQLite to exist in a temp dir, so we ingest a
# miniature snapshot before each assertion.

DATASET = Path("data/handcrafted/database_systems")


def _build_store(tmp_path: Path) -> Path:
    store_path = tmp_path / "world_model.sqlite"
    ingest(DATASET, store_path)
    return store_path


def test_fetch_concepts_returns_tree(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    concepts = fetch_concepts(topic="transaction", depth=2, store_path=store)
    assert concepts, "Expected concept tree results"
    assert any("transaction" in c["name"].lower() for c in concepts)


def test_search_events_filters_by_concept(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    events = search_events(concept_id="relational_model", limit=5, store_path=store)
    assert events, "Expected timeline events"
    assert all(evt["concept_id"] == "relational_model" for evt in events)


def test_lookup_paper_returns_authors(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    paper = lookup_paper("codd-1970", store_path=store)
    assert paper["id"] == "codd-1970"
    assert paper["authors"], "Paper should include author metadata"


def test_record_claim_persists(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    payload = record_claim(
        subject="relational_model",
        content="Test claim",
        citation="codd-1970",
        store_path=store,
    )
    assert payload["subject"] == "relational_model"
    db = WorldModelStore(store)
    rows = db.query("SELECT subject_id, body FROM claims WHERE body = ?", ("Test claim",))
    assert rows and rows[0][0] == "relational_model"
