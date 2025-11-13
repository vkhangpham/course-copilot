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
