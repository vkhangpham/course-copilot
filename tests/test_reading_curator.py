from pathlib import Path

from apps.orchestrator.ta_roles.reading_curator import ReadingCurator

DATASET_ROOT = Path("data/handcrafted/database_systems")


def test_reading_curator_from_dataset() -> None:
    curator = ReadingCurator()
    readings = curator.curate(DATASET_ROOT, limit=3)

    assert readings, "Expected curated readings"
    assert readings[0].title
    assert readings[0].citation


def test_reading_curator_filters_keywords(tmp_path: Path) -> None:
    papers_csv = tmp_path / "papers.csv"
    papers_csv.write_text(
        """id,title,authors,venue,year,key_points
alpha,Alpha Study,alice;bob,Conf,2020,"Explores transactions"
beta,Beta Paper,beta,betaConf,2021,"Discusses storage"
        """.strip(),
        encoding="utf-8",
    )

    curator = ReadingCurator()
    readings = curator.curate(tmp_path, keywords=["storage"])

    assert len(readings) == 1
    assert readings[0].identifier == "beta"
    assert "storage" in readings[0].why_it_matters.lower()
