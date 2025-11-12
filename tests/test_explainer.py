import yaml
from pathlib import Path

from apps.orchestrator.ta_roles.explainer import Explainer


DATASET_ROOT = Path("data/handcrafted/database_systems")


def test_explainer_uses_real_dataset():
    explainer = Explainer(dataset_root=DATASET_ROOT)
    chunks = explainer.write("Transactions and recovery", limit=2)
    assert chunks, "Explainer should emit chunks for the handcrafted dataset"
    assert any("history" in chunk.body_md.lower() for chunk in chunks)
    assert chunks[0].citations, "chunk should include citations"


def test_explainer_handles_custom_dataset(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    concepts_payload = {
        "concepts": {
            "acid": {
                "name": "ACID Properties",
                "summary": "Atomicity, consistency, isolation, durability define transactions.",
                "canonical_sources": ["paper-xyz"],
                "prerequisites": ["transactions"],
            }
        }
    }
    definitions_payload = {
        "definitions": [
            {
                "id": "def-acid",
                "concept": "acid",
                "text": "ACID ensures reliable transactions.",
                "citation": "paper-xyz",
            }
        ]
    }
    (dataset / "concepts.yaml").write_text(yaml.safe_dump(concepts_payload, sort_keys=False), encoding="utf-8")
    (dataset / "definitions.yaml").write_text(
        yaml.safe_dump(definitions_payload, sort_keys=False),
        encoding="utf-8",
    )
    (dataset / "timeline.csv").write_text(
        "event,year,why_it_matters,related_concepts,citation_id\n"
        "ACID published,1983,Established transaction guarantees,acid,paper-xyz\n",
        encoding="utf-8",
    )

    explainer = Explainer(dataset_root=dataset)
    chunks = explainer.write("ACID overview", limit=1)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert "Definition" in chunk.body_md
    assert "History" in chunk.body_md
    assert chunk.citations == ["paper-xyz"]
