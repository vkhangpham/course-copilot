import json
import tempfile
import unittest
from pathlib import Path

import yaml

from ccopilot.cli.run_poc import main as cli_main


def yaml_dump(data) -> str:
    return yaml.safe_dump(data, sort_keys=False)


class CLIRunPocTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self._prepare_repo()

    def _prepare_repo(self) -> None:
        (self.repo_root / "config").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "world_model").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "evals").mkdir(parents=True, exist_ok=True)
        dataset_dir = self.repo_root / "data" / "handcrafted" / "database_systems"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_dir = dataset_dir

        schema_path = self.repo_root / "world_model" / "schema.sql"
        schema_path.write_text("CREATE TABLE IF NOT EXISTS concepts(id TEXT PRIMARY KEY);\n", encoding="utf-8")
        rubrics_path = self.repo_root / "evals" / "rubrics.yaml"
        rubrics_path.write_text("rubrics: []\n", encoding="utf-8")
        quiz_bank = dataset_dir / "quiz_bank.json"

        pipeline_yaml = f"""
course:
  title: "CLI Test Course"
  duration_weeks: 3
  audience:
    persona: "Tester"
models:
  teacher_model: "gpt-4o"
notebook:
  api_base: "http://localhost:5055"
world_model:
  schema_path: "{schema_path}"
  dataset_dir: "{dataset_dir}"
  sqlite_path: "{self.repo_root / 'world_model' / 'state.sqlite'}"
evaluation:
  rubrics_path: "{rubrics_path}"
  quiz_bank_path: "{quiz_bank}"
"""
        (self.repo_root / "config" / "pipeline.yaml").write_text(pipeline_yaml.strip(), encoding="utf-8")
        self._seed_dataset(dataset_dir, quiz_bank)

    def _seed_dataset(self, dataset_dir: Path, quiz_bank: Path) -> None:
        (dataset_dir / "authors.csv").write_text(
            "id,full_name,affiliation\n"
            "author_a,Test Author,Test Lab\n",
            encoding="utf-8",
        )
        (dataset_dir / "papers.csv").write_text(
            "id,title,venue,year,url,authors\n"
            "paper_a,Test Paper,TestConf,2024,http://example.com,author_a\n",
            encoding="utf-8",
        )
        concepts_yaml = {
            "concepts": {
                "concept_a": {
                    "name": "Concept A",
                    "summary": "A sample concept",
                    "parent": None,
                    "prerequisites": [],
                    "canonical_sources": ["paper_a"],
                }
            }
        }
        (dataset_dir / "concepts.yaml").write_text(
            yaml_dump(concepts_yaml),
            encoding="utf-8",
        )
        (dataset_dir / "taxonomy.yaml").write_text(
            yaml_dump(
                {
                    "domains": [
                        {
                            "id": "foundation",
                            "title": "Foundation",
                            "concepts": ["concept_a"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (dataset_dir / "timeline.csv").write_text(
            "event,year,why_it_matters,related_concepts,citation_id\n"
            "\"Launch\",2024,\"Kickoff\",\"concept_a\",\"paper_a\"\n",
            encoding="utf-8",
        )
        quiz_bank.write_text('[{"id": "quiz_a", "learning_objectives": ["concept_a"]}]', encoding="utf-8")
        (dataset_dir / "citations.yaml").write_text(
            yaml_dump({"citations": {"paper_a": {"title": "Test Paper"}}}),
            encoding="utf-8",
        )
        (dataset_dir / "course_outline.yaml").write_text(
            yaml_dump({"weeks": [{"week": 1, "topic": "Intro"}]}),
            encoding="utf-8",
        )
        (dataset_dir / "graph.yaml").write_text(yaml_dump({"edges": []}), encoding="utf-8")
        (dataset_dir / "definitions.yaml").write_text(
            yaml_dump({"definitions": []}),
            encoding="utf-8",
        )

    def test_cli_run_produces_artifacts(self) -> None:
        output_dir = self.repo_root / "outputs"
        exit_code = cli_main(
            [
                "--config",
                str(self.repo_root / "config" / "pipeline.yaml"),
                "--repo-root",
                str(self.repo_root),
                "--output-dir",
                str(output_dir),
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((output_dir / "course_plan.md").exists())
        self.assertTrue((output_dir / "lectures" / "module_01.md").exists())
        artifacts_dir = output_dir / "artifacts"
        manifest_path = next(artifacts_dir.glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("dataset_summary", manifest)
        self.assertIn("world_model_store", manifest)

    def test_cli_dry_run_skips_artifacts(self) -> None:
        output_dir = self.repo_root / "outputs"
        exit_code = cli_main(
            [
                "--config",
                str(self.repo_root / "config" / "pipeline.yaml"),
                "--repo-root",
                str(self.repo_root),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertFalse((output_dir / "course_plan.md").exists())

    def test_cli_ingest_flag_refreshes_world_model(self) -> None:
        output_dir = self.repo_root / "outputs"
        sqlite_path = self.repo_root / "world_model" / "state.sqlite"
        if sqlite_path.exists():
            sqlite_path.unlink()
        exit_code = cli_main(
            [
                "--config",
                str(self.repo_root / "config" / "pipeline.yaml"),
                "--repo-root",
                str(self.repo_root),
                "--output-dir",
                str(output_dir),
                "--ingest-world-model",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(sqlite_path.exists())
        self.assertTrue((output_dir / "course_plan.md").exists())


if __name__ == "__main__":
    unittest.main()
