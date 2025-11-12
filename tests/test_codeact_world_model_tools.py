import tempfile
from pathlib import Path

from scripts.ingest_handcrafted import ingest
from apps.codeact.tools.world_model import (
    DEFAULT_STORE,
    append_timeline_event,
    fetch_concepts,
    link_concepts,
    list_claims,
    list_relationships,
    lookup_paper,
    persist_outline,
    record_claim,
    search_events,
)
from world_model.storage import WorldModelStore

# The tests expect the world-model SQLite to exist in a temp dir, so we ingest a
# miniature snapshot before each assertion.

DATASET = Path("data/handcrafted/database_systems")


def test_world_model_default_store_is_repo_relative() -> None:
    expected = (Path(__file__).resolve().parents[1] / "outputs" / "world_model" / "state.sqlite").resolve()
    assert DEFAULT_STORE == expected


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


def test_list_claims_returns_records(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    record_claim(subject="relational_model", content="Claim", citation=None, store_path=store)
    claims = list_claims(subject_id="relational_model", store_path=store)
    assert any(claim["subject_id"] == "relational_model" for claim in claims)


def test_list_relationships_filters(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    relationships = list_relationships(source_id="relational_model", store_path=store)
    assert relationships, "Expected relationship rows"
    assert relationships[0]["source_id"] == "relational_model"


def test_link_concepts_tool_adds_relationship(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rel = link_concepts(
        source_id="relational_model",
        target_id="schema_design",
        relation_type="reinforces",
        justification="Test",
        store_path=store,
    )
    assert rel["relation_type"] == "reinforces"
    db = WorldModelStore(store)
    rows = db.query(
        "SELECT relation_type FROM relationships WHERE id = ?",
        (rel["id"],),
    )
    assert rows[0][0] == "reinforces"


def test_append_timeline_event_tool_writes_row(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    event = append_timeline_event(
        event_label="CodeAct milestone",
        related_concept="relational_model",
        summary="Generated via CodeAct",
        event_year=2025,
        store_path=store,
    )
    db = WorldModelStore(store)
    rows = db.query(
        "SELECT event_label FROM observations WHERE id = ?",
        (event["id"],),
    )
    assert rows and rows[0][0] == "CodeAct milestone"


def test_persist_outline_tool_records_artifact(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    outline = {"weeks": [{"week": 1, "title": "Intro"}]}
    artifact = persist_outline(outline, version=2, store_path=store)
    assert artifact["payload"]["version"] == 2
    db = WorldModelStore(store)
    rows = db.query(
        "SELECT artifact_type FROM artifacts WHERE id = ?",
        (artifact["id"],),
    )
    assert rows and rows[0][0] == "course_outline"
