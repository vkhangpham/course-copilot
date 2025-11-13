from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from scripts.validate_handcrafted import app

runner = CliRunner()


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_yaml(path: Path, payload: dict | list) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _build_dataset(
    tmp_path: Path,
    *,
    bad_timeline: bool = False,
    quiz_warning: bool = False,
    bad_quiz_objective: bool = False,
) -> Path:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(
        dataset_dir / "authors.csv",
        ["id", "full_name", "affiliation"],
        [["author_a", "Author A", "Test Lab"]],
    )
    _write_csv(
        dataset_dir / "papers.csv",
        ["id", "title", "venue", "year", "url", "authors"],
        [["paper_a", "Paper A", "Conf", "2024", "http://example.com", "author_a"]],
    )

    concepts = {
        "concepts": {
            "concept_a": {
                "name": "Concept A",
                "summary": "Sample concept",
                "canonical_sources": ["paper_a"],
            }
        }
    }
    _write_yaml(dataset_dir / "concepts.yaml", concepts)

    taxonomy = {
        "domains": [
            {
                "id": "foundation",
                "title": "Foundation",
                "concepts": ["concept_a"],
            }
        ]
    }
    _write_yaml(dataset_dir / "taxonomy.yaml", taxonomy)
    _write_yaml(dataset_dir / "graph.yaml", {"edges": []})
    _write_yaml(dataset_dir / "definitions.yaml", {"definitions": []})
    _write_yaml(dataset_dir / "course_outline.yaml", {"weeks": []})

    related_concept = "unknown_concept" if bad_timeline else "concept_a"
    _write_csv(
        dataset_dir / "timeline.csv",
        ["event", "year", "related_concepts", "citation_id"],
        [["Launch", "2024", related_concept, "paper_a"]],
    )

    quiz_refs = ["missing-paper"] if quiz_warning else ["paper_a"]
    objectives = ["unknown_concept"] if bad_quiz_objective else ["concept_a"]
    legacy_concepts = ["concept_a"]
    quiz_bank = [
        {
            "id": "quiz_a",
            "learning_objectives": objectives,
            "concept_ids": legacy_concepts,
            "reference_papers": quiz_refs,
        }
    ]
    (dataset_dir / "quiz_bank.json").write_text(json.dumps(quiz_bank, indent=2), encoding="utf-8")
    return dataset_dir


def test_validate_handcrafted_cli_reports_errors(tmp_path: Path) -> None:
    dataset = _build_dataset(tmp_path, bad_timeline=True)
    result = runner.invoke(app, [str(dataset)], catch_exceptions=False)
    assert result.exit_code == 1
    assert "unknown concept" in result.stdout.lower()


def test_validate_handcrafted_cli_warns_but_passes_by_default(tmp_path: Path) -> None:
    dataset = _build_dataset(tmp_path, quiz_warning=True)
    result = runner.invoke(app, [str(dataset)], catch_exceptions=False)
    assert result.exit_code == 0
    assert "warning" in result.stdout.lower()


def test_validate_handcrafted_cli_catches_bad_quiz_objective(tmp_path: Path) -> None:
    dataset = _build_dataset(tmp_path, bad_quiz_objective=True)
    result = runner.invoke(app, [str(dataset)], catch_exceptions=False)
    assert result.exit_code == 1
    output = result.stdout.lower()
    assert "quiz" in output
    assert "unknown concept" in output
