from pathlib import Path

from ccopilot.core.config import load_course_constraints


def test_course_constraints_sample_loads() -> None:
    """Ensure the shipped constraints YAML matches CourseConstraints schema."""

    repo_root = Path(__file__).resolve().parents[1]
    sample_path = repo_root / "config" / "course_config.yaml"

    constraints = load_course_constraints(sample_path)

    assert constraints.title == "Database Systems"
    assert constraints.duration_weeks >= 1
    assert constraints.audience.persona == "upper-undergrad"
    assert "relational model" in constraints.focus_areas
