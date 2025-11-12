from pathlib import Path

import pytest

from apps.codeact.tools.data import load_dataset_asset, run_sql_query

DATASET_DIR = Path("data/handcrafted/database_systems")


def test_load_dataset_asset_json() -> None:
    asset = load_dataset_asset("quiz_bank.json", base_dir=DATASET_DIR)
    assert isinstance(asset, list)
    assert asset, "Expected quiz bank entries"


def test_load_dataset_asset_yaml() -> None:
    asset = load_dataset_asset("taxonomy.yaml", base_dir=DATASET_DIR)
    assert isinstance(asset, dict)
    assert "domains" in asset


def test_run_sql_query_reads_paper_metadata() -> None:
    rows = run_sql_query(
        "SELECT title FROM papers WHERE id='codd-1970'",
        dataset_dir=DATASET_DIR,
    )
    assert rows == [{"title": "A Relational Model of Data for Large Shared Data Banks"}]


def test_run_sql_query_handles_json_assets() -> None:
    rows = run_sql_query("SELECT COUNT(*) AS cnt FROM quiz_bank", dataset_dir=DATASET_DIR)
    assert rows and rows[0]["cnt"] >= 1


def test_run_sql_query_invalid_table_raises_value_error() -> None:
    with pytest.raises(ValueError):
        run_sql_query("SELECT * FROM imaginary_table", dataset_dir=DATASET_DIR)


def test_run_sql_query_rejects_empty_queries() -> None:
    with pytest.raises(ValueError):
        run_sql_query("   ", dataset_dir=DATASET_DIR)


def test_run_sql_query_exposes_concepts_table() -> None:
    rows = run_sql_query(
        "SELECT name FROM concepts WHERE id='relational_model'",
        dataset_dir=DATASET_DIR,
    )
    assert rows == [{"name": "Relational Model"}]


def test_run_sql_query_blocks_mutations() -> None:
    with pytest.raises(ValueError):
        run_sql_query("DROP TABLE papers", dataset_dir=DATASET_DIR)


def test_run_sql_query_exposes_definitions_table() -> None:
    rows = run_sql_query(
        "SELECT statement FROM definitions WHERE id='def-transaction'",
        dataset_dir=DATASET_DIR,
    )
    assert rows
    assert "transaction" in rows[0]["statement"].lower()


def test_run_sql_query_exposes_graph_edges_table() -> None:
    rows = run_sql_query(
        "SELECT relation_type FROM graph_edges WHERE source_id='relational_model'",
        dataset_dir=DATASET_DIR,
    )
    assert rows
    assert rows[0]["relation_type"]
