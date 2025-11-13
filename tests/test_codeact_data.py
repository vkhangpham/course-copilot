import os
import shutil
from pathlib import Path

import pytest

from apps.codeact.tools.data import load_dataset_asset, run_sql_query
from apps.codeact.tools_data import DataTools

DATASET_DIR = Path("data/handcrafted/database_systems")


def _seed_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    dataset_dir = repo_root / "data" / "handcrafted" / "database_systems"
    dataset_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DATASET_DIR, dataset_dir, dirs_exist_ok=True)
    return repo_root


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


def test_data_tools_run_sql_matches_function(tmp_path: Path) -> None:
    tools = DataTools(tmp_path, dataset_dir=DATASET_DIR)
    rows = tools.run_sql("SELECT COUNT(*) AS cnt FROM papers")
    assert rows and rows[0]["cnt"] >= 1


def test_load_dataset_asset_honors_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom_dataset = tmp_path / "dataset"
    shutil.copytree(DATASET_DIR, custom_dataset)
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(custom_dataset))
    asset = load_dataset_asset("taxonomy.yaml")
    assert isinstance(asset, dict)
    assert "domains" in asset


def test_run_sql_query_works_outside_repo_when_env_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_dataset = tmp_path / "dataset"
    shutil.copytree(DATASET_DIR, custom_dataset)
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(custom_dataset))
    cwd_before = Path.cwd()
    os.chdir(tmp_path)
    try:
        rows = run_sql_query("SELECT COUNT(*) AS cnt FROM authors")
    finally:
        os.chdir(cwd_before)
    assert rows and rows[0]["cnt"] >= 1


def test_load_dataset_asset_uses_repo_root_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _seed_repo_root(tmp_path)
    monkeypatch.delenv("COURSEGEN_DATASET_DIR", raising=False)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo_root))
    asset = load_dataset_asset("taxonomy.yaml")
    assert isinstance(asset, dict)
    assert asset.get("domains")


def test_run_sql_query_uses_repo_root_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _seed_repo_root(tmp_path)
    monkeypatch.delenv("COURSEGEN_DATASET_DIR", raising=False)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo_root))
    rows = run_sql_query("SELECT COUNT(*) AS cnt FROM authors")
    assert rows and rows[0]["cnt"] >= 1
