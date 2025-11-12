from pathlib import Path

import yaml

from apps.orchestrator.ta_roles.syllabus_designer import SyllabusDesigner

DATASET_ROOT = Path("data/handcrafted/database_systems")


def test_syllabus_designer_reads_course_outline() -> None:
    designer = SyllabusDesigner()
    modules = designer.propose_modules(DATASET_ROOT)

    assert modules, "Expected modules derived from course_outline.yaml"
    assert modules[0].title == "Relational Thinking & SQL Foundations"
    assert "relational model" in modules[0].outcomes[0].lower()


def test_syllabus_designer_fallbacks_to_taxonomy(tmp_path: Path) -> None:
    taxonomy = {
        "domains": [
            {
                "id": "core",
                "title": "Core Concepts",
                "concepts": ["transactions", "recovery"],
                "required_readings": ["codd-1970"],
            },
            {
                "id": "advanced",
                "title": "Advanced Topics",
                "concepts": ["distribution"],
            },
        ]
    }
    (tmp_path / "taxonomy.yaml").write_text(yaml.safe_dump(taxonomy), encoding="utf-8")

    designer = SyllabusDesigner()
    modules = designer.propose_modules(tmp_path)

    assert len(modules) == 2
    assert modules[0].title == "Core Concepts"
    assert any("transaction" in outcome for outcome in modules[0].outcomes)
    assert modules[0].readings == ["codd-1970"]


def test_syllabus_designer_defaults_when_no_data(tmp_path: Path) -> None:
    designer = SyllabusDesigner()
    modules = designer.propose_modules(tmp_path)

    assert len(modules) == 1
    assert modules[0].title == "Course Foundations"
