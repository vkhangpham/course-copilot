import tempfile
import unittest
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
            [("concept_seed", "Seed Concept", "Test summary", None)],
        )

    def test_record_claim_inserts_row(self) -> None:
        result = self.adapter.record_claim(
            subject="concept_seed",
            content="Seed concept summary",
            citation="paper_a",
        )
        self.assertEqual(result["subject"], "concept_seed")
        self.assertEqual(result["body"], "Seed concept summary")
        rows = self.adapter.store.query(
            "SELECT subject_id, body, citation FROM claims WHERE subject_id = ?",
            ("concept_seed",),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Seed concept summary")

    def test_fetch_concept_tree_returns_expected_fields(self) -> None:
        tree = self.adapter.fetch_concept_tree(topic="Seed", max_depth=0, limit=1)
        self.assertTrue(tree)
        node = tree[0]
        self.assertEqual(node["id"], "concept_seed")
        self.assertIn("children", node)
        self.assertIn("prerequisites", node)


if __name__ == "__main__":
    unittest.main()
