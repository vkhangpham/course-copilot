import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import scripts.query_world_model as wm_cli
from scripts.ingest_handcrafted import ingest

DATASET = Path("data/handcrafted/database_systems")
RUNNER = CliRunner()


def _build_store(tmp_path: Path) -> Path:
    store_path = tmp_path / "world_model.sqlite"
    ingest(DATASET, store_path)
    return store_path


def test_concepts_command_outputs_json(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(wm_cli.app, ["concepts", "--store", str(store), "--topic", "transaction", "--json"])
    assert result.exit_code == 0
    assert '"transaction_management"' in result.stdout


def test_concepts_command_missing_store_errors(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.sqlite"
    result = RUNNER.invoke(wm_cli.app, ["concepts", "--store", str(missing)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_concepts_command_honors_repo_root_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    store = repo_root / "outputs" / "world_model" / "state.sqlite"
    store.parent.mkdir(parents=True, exist_ok=True)
    ingest(DATASET, store)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo_root))
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    try:
        result = RUNNER.invoke(wm_cli.app, ["concepts", "--topic", "transaction", "--json"])
    finally:
        monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    assert result.exit_code == 0
    assert '"transaction_management"' in result.stdout


def test_concepts_command_honors_store_env_after_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    missing_store = tmp_path / "missing.sqlite"
    monkeypatch.setenv("WORLD_MODEL_STORE", str(missing_store))
    result = RUNNER.invoke(wm_cli.app, ["concepts", "--json"])
    assert result.exit_code != 0
    assert missing_store.name in result.output


def test_timeline_command_filters_and_outputs_json(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(
        wm_cli.app,
        ["timeline", "--store", str(store), "--concept", "relational_model", "--json"],
    )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "relational_model" in output
    assert '"year":' in output


def test_claims_command_returns_rows(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(
        wm_cli.app,
        ["claims", "relational_model", "--store", str(store), "--json"],
    )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "relational_model" in output
    assert "citation" in output


def test_papers_command_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(
        wm_cli.app,
        ["papers", "--store", str(store), "--keyword", "relational", "--json"],
    )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "relational model" in output


def test_authors_command_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(
        wm_cli.app,
        ["authors", "--store", str(store), "--keyword", "stonebraker", "--json"],
    )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "stonebraker" in output
    assert "uc berkeley" in output


def test_summary_command_outputs_counts(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = RUNNER.invoke(wm_cli.app, ["summary", "--store", str(store), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["counts"]["concepts"] > 0
    assert payload["artifacts_by_type"]
