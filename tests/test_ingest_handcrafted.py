import shutil
import sqlite3
from pathlib import Path

import pytest

from scripts import ingest_handcrafted as ingest

DATASET = Path("data/handcrafted/database_systems")


def _write_minimal_dataset(
    tmp_path: Path,
    *,
    timeline_header: str = "event",
    citation_header: str = "citation_id",
) -> Path:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    (dataset_dir / "authors.csv").write_text(
        "id,full_name,affiliation\nauthor_a,Test Author,Test Lab\n",
        encoding="utf-8",
    )
    (dataset_dir / "papers.csv").write_text(
        "id,title,venue,year,url,authors\npaper_a,Test Paper,TestConf,2024,http://example.com,author_a\n",
        encoding="utf-8",
    )
    (dataset_dir / "concepts.yaml").write_text(
        "concepts:\n  concept_a:\n    name: Concept A\n    summary: Sample\n    canonical_sources: [paper_a]\n",
        encoding="utf-8",
    )
    (dataset_dir / "taxonomy.yaml").write_text("domains: []\n", encoding="utf-8")
    (dataset_dir / "graph.yaml").write_text("edges: []\n", encoding="utf-8")
    (dataset_dir / "definitions.yaml").write_text("definitions: []\n", encoding="utf-8")
    (dataset_dir / "quiz_bank.json").write_text("[]", encoding="utf-8")

    timeline_columns = [
        "year",
        timeline_header,
        "why_it_matters",
        "related_concepts",
        citation_header,
    ]
    (dataset_dir / "timeline.csv").write_text(
        ",".join(timeline_columns) + "\n" + "1970,Milestone,Matters,concept_a,paper_a\n",
        encoding="utf-8",
    )
    return dataset_dir


def test_ingest_load_csv_preserves_rows_without_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text(
        "year,event_label,why_it_matters\n1970,Relational revolution,Formalizes relational algebra.\n",
        encoding="utf-8",
    )

    rows = ingest._load_csv(csv_path)

    assert len(rows) == 1
    assert rows[0]["event_label"] == "Relational revolution"


def test_ingest_load_csv_skips_empty_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "timeline.csv"
    csv_path.write_text(
        "year,event_label,why_it_matters\n , , \n1980,,\n",
        encoding="utf-8",
    )

    rows = ingest._load_csv(csv_path)

    assert len(rows) == 1
    assert rows[0]["year"] == "1980"


def test_ingest_timeline_uses_citation_column(tmp_path: Path) -> None:
    dataset_copy = tmp_path / "dataset"
    shutil.copytree(DATASET, dataset_copy)
    timeline_path = dataset_copy / "timeline.csv"
    timeline_path.write_text(
        "year,event,why_it_matters,related_concepts,citation_id,citation\n"
        "1970,Relational milestone,Formalizes algebra,relational_model,,codd-1970\n",
        encoding="utf-8",
    )

    store_path = tmp_path / "state.sqlite"
    ingest.ingest(dataset_copy, store_path)

    with sqlite3.connect(store_path) as conn:
        row = conn.execute(
            "SELECT citation FROM observations WHERE event_label=?",
            ("Relational milestone",),
        ).fetchone()

    assert row is not None
    assert row[0] == "codd-1970"


def test_load_datasets_supports_plain_citation_column(tmp_path: Path) -> None:
    dataset_dir = _write_minimal_dataset(tmp_path, citation_header="citation")
    datasets = ingest._load_datasets(dataset_dir)
    assert datasets["timeline"][0]["citation_id"] == "paper_a"


def test_load_datasets_accepts_comma_delimited_authors(tmp_path: Path) -> None:
    dataset_copy = tmp_path / "dataset"
    shutil.copytree(DATASET, dataset_copy)
    papers_path = dataset_copy / "papers.csv"
    text = papers_path.read_text(encoding="utf-8")
    text = text.replace("chamberlin;boyce", "chamberlin,boyce", 1)
    papers_path.write_text(text, encoding="utf-8")

    datasets = ingest._load_datasets(dataset_copy)
    target = next(row for row in datasets["papers"] if row["id"] == "system-r-1976")
    assert target["author_list"] == ["chamberlin", "boyce"]


def test_load_datasets_accepts_comma_delimited_related_concepts(tmp_path: Path) -> None:
    dataset_copy = tmp_path / "dataset"
    shutil.copytree(DATASET, dataset_copy)
    timeline_path = dataset_copy / "timeline.csv"
    text = timeline_path.read_text(encoding="utf-8")
    text = text.replace("relational_model;relational_algebra", "relational_model, relational_algebra", 1)
    timeline_path.write_text(text, encoding="utf-8")

    datasets = ingest._load_datasets(dataset_copy)

    assert datasets["timeline"][0]["concept_ids"] == ["relational_model", "relational_algebra"]


def test_ingest_timeline_accepts_event_label_column(tmp_path: Path) -> None:
    dataset_dir = _write_minimal_dataset(tmp_path, timeline_header="event_label")
    store_path = tmp_path / "state.sqlite"

    ingest.ingest(dataset_dir, store_path)

    with sqlite3.connect(store_path) as conn:
        label = conn.execute("SELECT event_label FROM observations").fetchone()[0]

    assert label == "Milestone"


def test_ingest_keeps_events_without_related_concepts(tmp_path: Path) -> None:
    dataset_dir = _write_minimal_dataset(tmp_path)
    timeline_path = dataset_dir / "timeline.csv"
    text = timeline_path.read_text(encoding="utf-8")
    timeline_path.write_text(text.replace("concept_a", ""), encoding="utf-8")

    store_path = tmp_path / "state.sqlite"
    ingest.ingest(dataset_dir, store_path)

    with sqlite3.connect(store_path) as conn:
        row = conn.execute("SELECT event_label, related_concept FROM observations").fetchone()

    assert row == ("Milestone", None)


def test_ingest_preserves_existing_store_on_failure(tmp_path: Path) -> None:
    dataset_dir = _write_minimal_dataset(tmp_path)
    store_path = tmp_path / "state.sqlite"
    ingest.ingest(dataset_dir, store_path)
    original_bytes = store_path.read_bytes()

    broken_dir = _write_minimal_dataset(tmp_path / "broken")
    timeline_path = broken_dir / "timeline.csv"
    timeline_path.write_text(
        "year,event,why_it_matters,related_concepts,citation_id\n1970,Broken,Matters,unknown_concept,paper_a\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        ingest.ingest(broken_dir, store_path)

    assert store_path.read_bytes() == original_bytes
