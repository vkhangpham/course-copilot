import tempfile
import unittest
from pathlib import Path

from world_model.storage import WorldModelStore


class WorldModelStoreTests(unittest.TestCase):
    def test_creates_parent_directory_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "state.sqlite"
            store = WorldModelStore(db_path)

            # Insert and fetch a concept to prove schema + connection are ready.
            store.execute_many(
                "INSERT INTO concepts(id, name) VALUES (?, ?)",
                [("concept:relational-model", "Relational Model")],
            )
            rows = store.query("SELECT id, name FROM concepts")

            self.assertTrue(db_path.exists())
            self.assertEqual(rows[0][0], "concept:relational-model")
            self.assertEqual(rows[0][1], "Relational Model")


if __name__ == "__main__":
    unittest.main()
