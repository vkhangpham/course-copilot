import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from ccopilot.core.dspy_runtime import DSPyModelHandles
from ccopilot.pipeline import bootstrap_pipeline, run_pipeline


class PipelineRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = {
            key: os.environ.get(key)
            for key in ("OPEN_NOTEBOOK_API_BASE", "OPEN_NOTEBOOK_API_KEY", "OPEN_NOTEBOOK_SLUG")
        }
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.config_path = self._write_pipeline_config()
        self.output_dir = self.repo_root / "outputs"
        self._dspy_handles = DSPyModelHandles(teacher=object(), ta=object(), student=object())
        patcher = mock.patch(
            "ccopilot.pipeline.bootstrap.configure_dspy_models",
            autospec=True,
            return_value=self._dspy_handles,
        )
        self.addCleanup(patcher.stop)
        self.mock_configure_dspy = patcher.start()
        self._codeact_registry = mock.Mock()
        self._codeact_registry.describe.return_value = {"programs": {}}
        registry_patcher = mock.patch(
            "ccopilot.pipeline.runtime.build_default_registry",
            autospec=True,
            return_value=self._codeact_registry,
        )
        self.addCleanup(registry_patcher.stop)
        self.mock_build_registry = registry_patcher.start()

    def tearDown(self) -> None:
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

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
        rubrics_payload = {
            "coverage": {
                "description": "Ensures foundational topics are present",
                "pass_threshold": 0.6,
                "checklist": [
                    "Mentions relational model and SQL fundamentals",
                    "Addresses transactions, recovery, and concurrency",
                    "Includes distributed/modern databases",
                ],
            },
            "grounding": {
                "description": "Checks for citations",
                "pass_threshold": 0.7,
                "checklist": [
                    "Every learning objective references at least one primary source",
                    "Claims cite papers from papers.csv",
                ],
            },
            "pedagogy": {
                "description": "Clarity of instruction",
                "pass_threshold": 0.7,
                "checklist": [
                    "States learning objectives and assessments",
                    "Includes worked examples and review questions",
                ],
            },
        }
        rubrics_path.write_text(yaml.safe_dump(rubrics_payload, sort_keys=False), encoding="utf-8")

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
  auth_token: "test-token"
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
        self.assertIs(ctx.dspy_handles, self._dspy_handles)
        artifacts = run_pipeline(ctx, dry_run=True)

        self.assertIsNone(artifacts)
        self.assertFalse((self.output_dir / "course_plan.md").exists())
        self.mock_build_registry.assert_not_called()

    def test_full_run_emits_stub_artifacts(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        self.assertIs(ctx.dspy_handles, self._dspy_handles)
        artifacts = run_pipeline(ctx, dry_run=False)

        self.assertIsNotNone(artifacts)
        assert artifacts is not None
        self.assertTrue(artifacts.course_plan.exists())
        self.assertTrue(artifacts.lecture.exists())
        self.assertTrue(artifacts.eval_report.exists())
        self.assertTrue(artifacts.provenance.exists())
        self.assertTrue(artifacts.manifest.exists())
        self.assertIsNotNone(artifacts.highlights)
        assert artifacts.highlights is not None
        self.assertTrue(artifacts.highlights.exists())

        plan_text = artifacts.course_plan.read_text(encoding="utf-8")
        self.assertIn("Test Course", plan_text)
        self.assertIn("Concept Highlights", plan_text)
        self.assertIn("concept_a", plan_text)

        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["course_plan"], str(artifacts.course_plan))
        self.assertEqual(manifest["lecture"], str(artifacts.lecture))
        highlights = manifest.get("world_model_highlights")
        self.assertIsNotNone(highlights)
        assert highlights is not None
        self.assertIn("concepts", highlights)
        self.assertTrue(any(entry["id"] == "concept_a" for entry in highlights["concepts"]))
        self.assertIn("syllabus_modules", highlights)
        self.assertIn("reading_list", highlights)
        self.mock_build_registry.assert_called_once_with(dspy_handles=self._dspy_handles)
        self.assertIn("exercise_ideas", highlights)
        self.assertIn("explanations", highlights)
        self.assertEqual(
            manifest.get("world_model_highlight_artifact"),
            str(artifacts.highlights),
        )
        self.assertIn("evaluation", manifest)
        self.assertTrue(manifest["evaluation"].get("use_students"))

        eval_record = json.loads(artifacts.eval_report.read_text(encoding="utf-8").splitlines()[0])
        self.assertTrue(eval_record["use_students"])
        self.assertGreaterEqual(eval_record.get("overall_score", 0), 0)
        self.assertGreater(len(eval_record.get("rubrics", [])), 0)

        highlight_payload = json.loads(artifacts.highlights.read_text(encoding="utf-8"))
        self.assertIn("world_model_highlights", highlight_payload)
        self.assertTrue(highlight_payload["world_model_highlights"].get("concepts"))
        self.assertTrue(highlight_payload["world_model_highlights"].get("syllabus_modules"))
        self.assertTrue(highlight_payload["world_model_highlights"].get("reading_list"))
        self.assertTrue(highlight_payload["world_model_highlights"].get("exercise_ideas"))
        self.assertTrue(highlight_payload["world_model_highlights"].get("explanations"))

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

    def test_student_ablation_skips_eval(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_students",
        )
        artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        eval_record = json.loads(artifacts.eval_report.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(eval_record["use_students"])
        self.assertEqual(eval_record["status"], "students_disabled")

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

    def test_bootstrap_sets_notebook_env(self) -> None:
        os.environ.pop("OPEN_NOTEBOOK_API_BASE", None)
        os.environ.pop("OPEN_NOTEBOOK_API_KEY", None)
        os.environ.pop("OPEN_NOTEBOOK_SLUG", None)

        bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )

        self.assertEqual(os.environ["OPEN_NOTEBOOK_API_BASE"], "http://localhost:5055")
        self.assertEqual(os.environ["OPEN_NOTEBOOK_API_KEY"], "test-token")
        self.assertEqual(os.environ["OPEN_NOTEBOOK_SLUG"], "test-notebook")

    def test_dataset_highlights_present_when_world_model_disabled(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_world_model",
        )
        artifacts = run_pipeline(ctx, dry_run=False)

        self.assertIsNotNone(artifacts)
        assert artifacts is not None
        self.assertIsNotNone(artifacts.highlights)

        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        highlights = manifest.get("world_model_highlights")
        self.assertIsNotNone(highlights)
        assert highlights is not None
        self.assertIn("syllabus_modules", highlights)
        self.assertNotIn("concepts", highlights)
        self.assertIn("explanations", highlights)
        self.assertEqual(
            manifest.get("world_model_highlight_artifact"),
            str(artifacts.highlights),
        )


if __name__ == "__main__":
    unittest.main()
