import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from ccopilot.pipeline import bootstrap_pipeline, run_pipeline


class PipelineRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.config_path = self._write_pipeline_config()
        self.output_dir = self.repo_root / "outputs"

    def _write_pipeline_config(self) -> Path:
        wm_dir = self.repo_root / "world_model"
        wm_dir.mkdir(parents=True)
        schema_path = wm_dir / "schema.sql"
        schema_path.write_text("CREATE TABLE IF NOT EXISTS concepts(id TEXT PRIMARY KEY);\n", encoding="utf-8")

        dataset_dir = self.repo_root / "data" / "handcrafted"
        dataset_dir.mkdir(parents=True)
        self._seed_dataset(dataset_dir)

        eval_dir = self.repo_root / "evals"
        eval_dir.mkdir(parents=True)
        rubrics_path = eval_dir / "rubrics.yaml"
        rubrics_path.write_text("rubrics: []\n", encoding="utf-8")

        quiz_bank = self.repo_root / "quiz_bank.json"
        quiz_bank.write_text("[]\n", encoding="utf-8")

        config_text = f"""
course:
  title: "Test Course"
  description: "Stub config for pipeline tests."
  duration_weeks: 4
  focus_areas: ["Area A"]
  tone: mentor
  audience:
    persona: "Tester"
    prior_knowledge: ["SQL"]
    goals: ["Ship capstone"]
  required_sources: []
  learning_objectives:
    - "Explain SQL basics"
models:
  teacher_model: gpt-4o
  ta_model: gpt-4o-mini
  student_model: gpt-4o-mini
  temperature: 0.1
  max_tokens: 512
notebook:
  api_base: "http://localhost:5055"
  notebook_slug: "test-notebook"
world_model:
  schema_path: "{schema_path}"
  dataset_dir: "{dataset_dir}"
  sqlite_path: "{wm_dir / 'state.sqlite'}"
evaluation:
  rubrics_path: "{rubrics_path}"
  quiz_bank_path: "{quiz_bank}"
  max_mutations: 1
"""
        config_path = self.repo_root / "pipeline.yaml"
        config_path.write_text(config_text.strip(), encoding="utf-8")
        return config_path

    def _seed_dataset(self, dataset_dir: Path) -> None:
        (dataset_dir / "authors.csv").write_text(
            "id,full_name,affiliation\n"
            "author_a,Author A,Lab\n",
            encoding="utf-8",
        )
        (dataset_dir / "papers.csv").write_text(
            "id,title,venue,year,url,authors\n"
            "paper_a,Title,Conf,2024,http://example.com,author_a\n",
            encoding="utf-8",
        )
        concepts_yaml = {
            "concepts": {
                "concept_a": {
                    "name": "Concept A",
                    "summary": "Summary",
                    "canonical_sources": ["paper_a"],
                }
            }
        }
        (dataset_dir / "concepts.yaml").write_text(
            yaml.safe_dump(concepts_yaml, sort_keys=False),
            encoding="utf-8",
        )
        (dataset_dir / "taxonomy.yaml").write_text(
            yaml.safe_dump({"domains": [{"id": "foundation", "concepts": ["concept_a"]}]}),
            encoding="utf-8",
        )
        (dataset_dir / "graph.yaml").write_text(
            yaml.safe_dump({"edges": []}),
            encoding="utf-8",
        )
        (dataset_dir / "definitions.yaml").write_text(
            yaml.safe_dump({"definitions": []}),
            encoding="utf-8",
        )
        (dataset_dir / "timeline.csv").write_text(
            "event,year,why_it_matters,related_concepts,citation_id\n"
            "\"Milestone\",2024,\"Matters\",\"concept_a\",\"paper_a\"\n",
            encoding="utf-8",
        )
        (dataset_dir / "quiz_bank.json").write_text(
            '[{"id": "quiz_a", "learning_objectives": ["concept_a"]}]',
            encoding="utf-8",
        )
        (dataset_dir / "course_outline.yaml").write_text(
            yaml.safe_dump({"weeks": []}),
            encoding="utf-8",
        )

    def test_dry_run_skips_artifacts(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        artifacts = run_pipeline(ctx, dry_run=True)

        self.assertIsNone(artifacts)
        self.assertFalse((self.output_dir / "course_plan.md").exists())

    def test_full_run_emits_stub_artifacts(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        artifacts = run_pipeline(ctx, dry_run=False)

        self.assertIsNotNone(artifacts)
        assert artifacts is not None
        self.assertTrue(artifacts.course_plan.exists())
        self.assertTrue(artifacts.lecture.exists())
        self.assertTrue(artifacts.eval_report.exists())
        self.assertTrue(artifacts.provenance.exists())
        self.assertTrue(artifacts.manifest.exists())

        plan_text = artifacts.course_plan.read_text(encoding="utf-8")
        self.assertIn("Test Course", plan_text)

        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["course_plan"], str(artifacts.course_plan))
        self.assertEqual(manifest["lecture"], str(artifacts.lecture))

    def test_missing_store_triggers_auto_ingest(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        sqlite_path = ctx.config.world_model.sqlite_path
        if sqlite_path.exists():
            sqlite_path.unlink()

        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        self.assertTrue(sqlite_path.exists(), "Bootstrap should auto-ingest when store is missing")

    def test_missing_dataset_dir_raises(self) -> None:
        dataset_dir = self.repo_root / "data"
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)

        with self.assertRaises(FileNotFoundError):
            bootstrap_pipeline(
                config_path=self.config_path,
                repo_root=self.repo_root,
                output_dir=self.output_dir,
            )


if __name__ == "__main__":
    unittest.main()
