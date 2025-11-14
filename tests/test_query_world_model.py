import importlib
from pathlib import Path

import json

import pytest
from typer.testing import CliRunner

from scripts.ingest_handcrafted import ingest
import scripts.query_world_model as query_world_model

DATASET = Path(__file__).resolve().parents[1] / "data" / "handcrafted" / "database_systems"


def _build_store(tmp_path: Path) -> Path:
    store = tmp_path / "state.sqlite"
    ingest(DATASET, store)
    return store


def test_query_world_model_default_matches_ingest_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    module = importlib.reload(query_world_model)
    expected = (Path(__file__).resolve().parents[1] / "outputs" / "world_model" / "state.sqlite").resolve()
    assert module.DEFAULT_STORE == expected


def test_query_world_model_repo_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom_root = tmp_path / "repo"
    custom_root.mkdir()
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(custom_root))
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    module = importlib.reload(query_world_model)
    expected = (custom_root / "outputs" / "world_model" / "state.sqlite").resolve()
    assert module.DEFAULT_STORE == expected
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    importlib.reload(query_world_model)


def test_query_world_model_store_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom_store = (tmp_path / "alt" / "custom.sqlite")
    monkeypatch.setenv("WORLD_MODEL_STORE", str(custom_store))
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(tmp_path / "repo"))
    module = importlib.reload(query_world_model)
    assert module.DEFAULT_STORE == custom_store.resolve()
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    importlib.reload(query_world_model)


def test_query_world_model_detects_repo_from_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = importlib.reload(query_world_model)
    marker = ".repo-marker"
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "outputs" / "world_model").mkdir(parents=True)
    (fake_repo / marker).write_text("repo")
    monkeypatch.setattr(module, "REPO_SENTINELS", (marker,), raising=False)
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    monkeypatch.chdir(fake_repo)
    try:
        repo_root = module._resolve_repo_root()
        assert repo_root == fake_repo.resolve()
        default_store = module._resolve_default_store()
        assert default_store == (fake_repo / "outputs" / "world_model" / "state.sqlite").resolve()
    finally:
        importlib.reload(query_world_model)


def test_resolve_repo_root_uses_module_root_when_cwd_outside_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = importlib.reload(query_world_model)
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    expected_root = Path(__file__).resolve().parents[1].resolve()
    monkeypatch.chdir(tmp_path)
    repo_root = module._resolve_repo_root()
    assert repo_root == expected_root
    default_store = module._resolve_default_store()
    expected_store = (expected_root / "outputs" / "world_model" / "state.sqlite").resolve()
    assert default_store == expected_store
    importlib.reload(query_world_model)


def test_summary_help_uses_generic_default_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    monkeypatch.delenv("WORLD_MODEL_STORE", raising=False)
    module = importlib.reload(query_world_model)
    result = CliRunner().invoke(module.app, ["summary", "--help"])
    assert result.exit_code == 0
    output = result.output
    assert module.STORE_ENV_VAR in output
    assert module.ENV_REPO_ROOT in output
    assert module.DEFAULT_STORE_RELATIVE.as_posix() in output
    assert str(module.DEFAULT_STORE) not in output


def test_search_repo_root_skips_unrelated_pyproject(tmp_path: Path) -> None:
    module = importlib.reload(query_world_model)
    unrelated = tmp_path / "unrelated_project"
    unrelated.mkdir()
    (unrelated / "pyproject.toml").write_text("[tool.poetry]\nname='other'\n", encoding="utf-8")
    assert module._search_repo_root(unrelated) is None


def test_search_repo_root_accepts_coursegen_like_structure(tmp_path: Path) -> None:
    module = importlib.reload(query_world_model)
    candidate = tmp_path / "coursegen_clone"
    config_dir = candidate / "config"
    config_dir.mkdir(parents=True)
    (candidate / "pyproject.toml").write_text("[tool.poetry]\nname='course-copilot'\n", encoding="utf-8")
    (config_dir / "pipeline.yaml").write_text("# pipeline\n", encoding="utf-8")
    found = module._search_repo_root(candidate)
    assert found == candidate.resolve()


def test_query_concepts_filters_by_topic(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_concepts(store, topic="transaction")
    assert any("Transaction" in row["name"] for row in rows)


def test_query_timeline_filters_by_concept_and_year(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    concept_id = "relational_model"
    rows = query_world_model.query_timeline(store, concept_id, year=1970)
    assert rows, "Expected timeline rows for relational_model"
    assert all(row["concept"] == concept_id for row in rows)
    assert all(row["year"] == 1970 for row in rows)


def test_query_claims_returns_definitions(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_claims(store, "relational_model")
    assert rows, "Relational model should have at least one stored claim"
    first = rows[0]
    assert first["concept"] == "relational_model"
    assert first["citation"]


def test_query_claims_handles_missing_concept(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_claims(store, "nonexistent_concept")
    assert rows == []


def test_query_claims_without_filter_returns_rows(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_claims(store, None, limit=5)
    assert rows
    assert all("concept" in row for row in rows)


def test_query_papers_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_papers(store, keyword="relational")
    assert rows, "Expected at least one relational paper"
    assert all("relational" in row["title"].lower() for row in rows)


def test_query_authors_filters_by_keyword(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_authors(store, keyword="stonebraker")
    assert rows == [
        {
            "id": "stonebraker",
            "name": "Michael Stonebraker",
            "affiliation": "UC Berkeley",
        }
    ]


def test_query_definitions_returns_rows(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_definitions(store, concept_id="transaction_management")
    assert rows
    assert rows[0]["concept"] == "transaction_management"


def test_query_graph_edges_filters_on_concept(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_graph_edges(store, concept_id="relational_model")
    assert rows
    assert all(
        row["source"] == "relational_model" or row["target"] == "relational_model"
        for row in rows
    )


def test_query_artifacts_filters_by_type(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    rows = query_world_model.query_artifacts(store, artifact_type="quiz_bank")
    assert rows
    assert rows[0]["type"] == "quiz_bank"


def test_query_summary_returns_counts(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    summary = query_world_model.query_summary(store)
    assert summary["counts"]["concepts"] > 0
    assert summary["artifacts_by_type"]
    details = summary["artifact_details"]
    assert details["quiz_bank"]["questions"] > 0
    assert details["course_outline"]["weeks"] > 0


runner = CliRunner()


def test_summary_cli_json(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    result = runner.invoke(query_world_model.app, ["summary", "--store", str(store), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["counts"]["concepts"] > 0
    assert payload["artifact_details"]["quiz_bank"]["questions"] > 0


def test_query_summary_reports_counts(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    summary = query_world_model.query_summary(store)
    counts = summary["counts"]
    assert counts["concepts"] > 0
    assert counts["artifacts"] >= 0
    assert summary["artifacts_by_type"]
    assert Path(summary["store"]).exists()
