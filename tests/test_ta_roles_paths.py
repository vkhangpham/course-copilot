from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from apps.orchestrator.ta_roles.dataset_paths import resolve_dataset_root
from apps.orchestrator.ta_roles.exercise_author import ExerciseAuthor
from apps.orchestrator.ta_roles.explainer import Explainer


def _seed_dataset(dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "quiz_bank.json").write_text(
        json.dumps(
            [
                {
                    "id": "quiz-1",
                    "prompt": "Explain transactions",
                    "learning_objectives": ["transaction_management"],
                    "difficulty": "medium",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    concepts = {
        "concepts": {
            "transaction_management": {
                "name": "Transaction Management",
                "summary": "Guarantees consistency via ACID semantics.",
                "canonical_sources": ["paper_a"],
            }
        }
    }
    (dataset_dir / "concepts.yaml").write_text(yaml.safe_dump(concepts, sort_keys=False), encoding="utf-8")
    (dataset_dir / "definitions.yaml").write_text(
        yaml.safe_dump({"definitions": [{"concept": "transaction_management", "text": "Definition text."}]}, sort_keys=False),
        encoding="utf-8",
    )
    (dataset_dir / "timeline.csv").write_text(
        "event,year,related_concepts,citation_id\n"
        "System R,1976,\"transaction_management\",\"paper_a\"\n",
        encoding="utf-8",
    )


def test_exercise_author_uses_repo_root_fallback(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    dataset_dir = repo_root / "data" / "handcrafted" / "database_systems"
    _seed_dataset(dataset_dir)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo_root))
    monkeypatch.delenv("COURSEGEN_DATASET_DIR", raising=False)

    other_cwd = tmp_path / "outside"
    other_cwd.mkdir()
    cwd_before = Path.cwd()
    os.chdir(other_cwd)
    try:
        author = ExerciseAuthor()
        exercises = author.draft(limit=1)
    finally:
        os.chdir(cwd_before)

    assert exercises, "Expected exercises even when running outside the repo root"


def test_resolve_dataset_root_prefers_env(monkeypatch, tmp_path: Path) -> None:
    dataset = tmp_path / "custom_dataset"
    dataset.mkdir()
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(dataset))
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)

    resolved = resolve_dataset_root()
    assert resolved == dataset.resolve()


def test_resolve_dataset_root_uses_repo_root(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo_root))
    monkeypatch.delenv("COURSEGEN_DATASET_DIR", raising=False)

    resolved = resolve_dataset_root()
    expected = (repo_root / "data" / "handcrafted" / "database_systems").resolve()
    assert resolved == expected


def test_resolve_dataset_root_respects_repo_root_parameter(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("COURSEGEN_DATASET_DIR", raising=False)
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)
    repo_root = tmp_path / "explicit"
    repo_root.mkdir(parents=True, exist_ok=True)

    resolved = resolve_dataset_root(repo_root=repo_root)
    expected = (repo_root / "data" / "handcrafted" / "database_systems").resolve()
    assert resolved == expected


def test_resolve_dataset_root_env_overrides_repo_param(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    dataset_override = tmp_path / "dataset"
    dataset_override.mkdir()
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(dataset_override))

    resolved = resolve_dataset_root(repo_root=repo_root)
    assert resolved == dataset_override.resolve()

def test_explainer_honors_dataset_env(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = tmp_path / "custom_dataset"
    _seed_dataset(dataset_dir)
    monkeypatch.setenv("COURSEGEN_DATASET_DIR", str(dataset_dir))
    monkeypatch.delenv("COURSEGEN_REPO_ROOT", raising=False)

    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    cwd_before = Path.cwd()
    os.chdir(other_cwd)
    try:
        explainer = Explainer()
        chunks = explainer.write("Transactions", limit=1)
    finally:
        os.chdir(cwd_before)

    assert chunks and chunks[0].heading.startswith("Transaction"), "Explainer should load dataset via env override"
