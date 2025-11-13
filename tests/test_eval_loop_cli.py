from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from apps.orchestrator import eval_loop


def _seed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    lectures_dir = repo / "outputs" / "lectures"
    lectures_dir.mkdir(parents=True, exist_ok=True)
    (lectures_dir / "demo.md").write_text("# Demo\n\nThis lecture mentions demo coverage.", encoding="utf-8")

    evals_dir = repo / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    rubrics_yaml = """
coverage:
  description: Coverage
  checklist:
    - demo
"""
    (evals_dir / "rubrics.yaml").write_text(rubrics_yaml.strip(), encoding="utf-8")
    return repo


def test_eval_loop_defaults_use_repo_root(monkeypatch, tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(eval_loop.app, ["--repo-root", str(repo), "--quiet"])
    assert result.exit_code == 0
    eval_dir = repo / "outputs" / "evaluations"
    assert any(eval_dir.glob("eval-*.jsonl"))


def test_eval_loop_honors_repo_root_env(monkeypatch, tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(repo))
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(eval_loop.app, ["--quiet"])
    assert result.exit_code == 0


def test_eval_loop_overrides_existing_repo_root_env(monkeypatch, tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)
    stale_repo = tmp_path / "stale"
    stale_repo.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(stale_repo))
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(eval_loop.app, ["--repo-root", str(repo), "--quiet"])
    assert result.exit_code == 0
    assert os.environ["COURSEGEN_REPO_ROOT"] == str(repo.resolve())
