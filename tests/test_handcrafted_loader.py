from pathlib import Path

from scripts.handcrafted_loader import load_dataset, validate_dataset

DATASET_DIR = Path("data/handcrafted/database_systems")


def test_load_dataset_smoke() -> None:
    dataset = load_dataset(DATASET_DIR)
    assert dataset.concepts, "Concepts should load"
    assert dataset.papers, "Papers should load"
    assert dataset.authors, "Authors should load"
    assert dataset.course_outline.get("weeks"), "Course outline weeks should be present"


def test_validate_dataset_clean() -> None:
    dataset = load_dataset(DATASET_DIR)
    errors, warnings = validate_dataset(dataset)
    assert errors == [], f"Expected no errors, got: {errors}"
    assert warnings == [], f"Expected no warnings, got: {warnings}"


def test_validate_dataset_flags_unknown_course_outline_concept(tmp_path: Path) -> None:
    dataset = load_dataset(DATASET_DIR)
    bogus_module = {
        "week": 99,
        "concept_ids": ["nonexistent"],
        "required_readings": ["codd-1970"],
    }
    dataset.course_outline.setdefault("weeks", []).append(bogus_module)
    errors, _ = validate_dataset(dataset)
    assert any("course outline module" in err.lower() for err in errors)


def test_validate_dataset_rejects_unknown_graph_citation(tmp_path: Path) -> None:
    dataset = load_dataset(DATASET_DIR)
    bad_edge = dict(dataset.graph.get("edges", [])[0])
    bad_edge["citations"] = ["unknown-paper"]
    dataset.graph.setdefault("edges", []).append(bad_edge)
    errors, _ = validate_dataset(dataset)
    assert any("unknown-paper" in err.lower() for err in errors)


def test_validate_dataset_reports_graph_citation_once(tmp_path: Path) -> None:
    dataset = load_dataset(DATASET_DIR)
    bad_edge = dict(dataset.graph.get("edges", [])[0])
    bad_edge["citations"] = ["missing-paper"]
    dataset.graph.setdefault("edges", []).append(bad_edge)
    errors, _ = validate_dataset(dataset)
    citation_errors = [err for err in errors if "missing-paper" in err.lower()]
    assert citation_errors, "Expected at least one citation error"
    assert len(citation_errors) == 1, f"Duplicate citation errors detected: {citation_errors}"
