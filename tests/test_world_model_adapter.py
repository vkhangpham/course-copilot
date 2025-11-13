import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from world_model.adapters import WorldModelAdapter


class WorldModelAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "state.sqlite"
        self.adapter = WorldModelAdapter(self.store_path)
        self._seed_concept()

    def _seed_concept(self) -> None:
        self.adapter.store.execute_many(
            "INSERT INTO concepts(id, name, summary, parent_id) VALUES (?, ?, ?, ?)",
            [
                ("concept_seed", "Seed Concept", "Test summary", None),
                ("concept_target", "Target Concept", "Target summary", None),
            ],
        )

    def test_record_claim_inserts_row(self) -> None:
        result = self.adapter.record_claim(
            subject="concept_seed",
            content="Seed concept summary",
            citation="paper_a",
        )
        self.assertEqual(result["subject"], "concept_seed")
        self.assertEqual(result["body"], "Seed concept summary")
        self.assertAlmostEqual(result["confidence"], 0.5)
        rows = self.adapter.store.query(
            "SELECT subject_id, body, citation, confidence FROM claims WHERE subject_id = ?",
            ("concept_seed",),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Seed concept summary")
        self.assertAlmostEqual(rows[0][3], 0.5)

    def test_record_claim_accepts_custom_confidence_and_timestamp(self) -> None:
        ts = datetime.now(timezone.utc)
        result = self.adapter.record_claim(
            subject="concept_seed",
            content="Custom confidence",
            confidence=0.9,
            asserted_at=ts,
        )
        self.assertAlmostEqual(result["confidence"], 0.9)
        self.assertEqual(result["asserted_at"], ts.isoformat())
        rows = self.adapter.store.query(
            "SELECT confidence, asserted_at FROM claims WHERE id = ?",
            (result["id"],),
        )
        self.assertAlmostEqual(rows[0][0], 0.9)
        self.assertEqual(rows[0][1], ts.isoformat())

    def test_record_claim_detects_contradictions(self) -> None:
        self.adapter.record_claim(subject="concept_seed", content="ACID is safe")
        result = self.adapter.record_claim(subject="concept_seed", content="ACID is not safe")
        self.assertTrue(result["contradicts"])

    def test_list_claims_filters_by_subject(self) -> None:
        self.adapter.record_claim(subject="concept_seed", content="Claim A", citation=None)
        claims = self.adapter.list_claims(subject_id="concept_seed")
        self.assertTrue(claims)
        self.assertEqual(claims[0]["subject_id"], "concept_seed")
        self.assertIn("confidence", claims[0])

    def test_list_relationships_returns_rows(self) -> None:
        self.adapter.store.execute_many(
            "INSERT INTO relationships(source_id, target_id, relation_type, justification) VALUES (?, ?, ?, ?)",
            [("concept_seed", "concept_parent", "prerequisite", "reference")],
        )
        relationships = self.adapter.list_relationships(source_id="concept_seed")
        self.assertTrue(relationships)
        self.assertEqual(relationships[0]["relation_type"], "prerequisite")

    def test_fetch_concept_tree_returns_expected_fields(self) -> None:
        tree = self.adapter.fetch_concept_tree(topic="Seed", max_depth=0, limit=1)
        self.assertTrue(tree)
        node = tree[0]
        self.assertEqual(node["id"], "concept_seed")
        self.assertIn("children", node)
        self.assertIn("prerequisites", node)

    def test_link_concepts_creates_relationship(self) -> None:
        payload = self.adapter.link_concepts(
            source_id="concept_seed",
            target_id="concept_target",
            relation_type="supports",
            justification="Added in test",
        )
        self.assertEqual(payload["relation_type"], "supports")
        rows = self.adapter.store.query(
            "SELECT source_id, target_id, relation_type FROM relationships WHERE id = ?",
            (payload["id"],),
        )
        self.assertEqual(rows[0][0], "concept_seed")

    def test_append_timeline_event_persists_row(self) -> None:
        event = self.adapter.append_timeline_event(
            event_label="Test Event",
            related_concept="concept_seed",
            summary="Summary",
            event_year=2024,
            citation="codd-1970",
        )
        self.assertEqual(event["event"], "Test Event")
        rows = self.adapter.store.query(
            "SELECT event_label, related_concept FROM observations WHERE id = ?",
            (event["id"],),
        )
        self.assertEqual(rows[0][1], "concept_seed")

    def test_persist_outline_records_artifact(self) -> None:
        outline = {"weeks": [{"week": 1, "title": "Intro"}]}
        artifact = self.adapter.persist_outline(outline, version=1)
        self.assertEqual(artifact["payload"]["version"], 1)
        rows = self.adapter.store.query(
            "SELECT artifact_type, metadata FROM artifacts WHERE id = ?",
            (artifact["id"],),
        )
        metadata = json.loads(rows[0][1])
        self.assertEqual(rows[0][0], "course_outline")
        self.assertEqual(metadata["outline"], outline)


if __name__ == "__main__":
    unittest.main()
