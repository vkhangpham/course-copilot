import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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
        rubrics_payload = {
            "coverage": {
                "description": "Coverage",
                "pass_threshold": 0.6,
                "checklist": [
                    "Mentions relational model and SQL fundamentals",
                    "Addresses transactions, recovery, and concurrency",
                    "Includes distributed/modern databases",
                ],
            },
            "grounding": {
                "description": "Grounding",
                "pass_threshold": 0.7,
                "checklist": [
                    "Every learning objective references at least one primary source",
                    "Claims cite papers from papers.csv",
                ],
            },
            "pedagogy": {
                "description": "Pedagogy",
                "pass_threshold": 0.7,
                "checklist": [
                    "States learning objectives and assessments",
                    "Includes worked examples and review questions",
                ],
            },
        }
        rubrics_path.write_text(yaml_dump(rubrics_payload), encoding="utf-8")
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

    def _run_cli(self, extra_args: list[str] | None = None) -> tuple[int, str, Path]:
        output_dir = self.repo_root / "outputs"
        args = [
            "--config",
            str(self.repo_root / "config" / "pipeline.yaml"),
            "--repo-root",
            str(self.repo_root),
            "--output-dir",
            str(output_dir),
        ]
        if extra_args:
            args.extend(extra_args)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli_main(args)
        return exit_code, buffer.getvalue(), output_dir

    def test_cli_run_produces_artifacts(self) -> None:
        exit_code, output, output_dir = self._run_cli()
        self.assertEqual(exit_code, 0)
        self.assertTrue((output_dir / "course_plan.md").exists())
        self.assertTrue((output_dir / "lectures" / "module_01.md").exists())
        artifacts_dir = output_dir / "artifacts"
        manifest_path = next(artifacts_dir.glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("dataset_summary", manifest)
        self.assertIn("world_model_store", manifest)
        highlights = manifest.get("world_model_highlights")
        self.assertIsNotNone(highlights)
        assert highlights is not None
        self.assertIn("concepts", highlights)
        plan_text = (output_dir / "course_plan.md").read_text(encoding="utf-8")
        self.assertIn("Concept Highlights", plan_text)
        self.assertTrue(manifest["evaluation"].get("use_students"))

        eval_report = output_dir / "evaluations"
        report_path = next(eval_report.glob("run-*.jsonl"))
        eval_payload = json.loads(report_path.read_text().splitlines()[0])
        self.assertIn("overall_score", eval_payload)
        self.assertIn("[eval] overall=", output)
        self.assertIn("[highlights] saved to", output)

    def test_cli_dry_run_skips_artifacts(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--dry-run"])
        self.assertEqual(exit_code, 0)
        self.assertFalse((output_dir / "course_plan.md").exists())
        self.assertNotIn("[eval]", output)
        self.assertNotIn("[highlights]", output)

    def test_cli_ingest_flag_refreshes_world_model(self) -> None:
        sqlite_path = self.repo_root / "world_model" / "state.sqlite"
        if sqlite_path.exists():
            sqlite_path.unlink()
        exit_code, output, output_dir = self._run_cli(["--ingest-world-model"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(sqlite_path.exists())
        self.assertTrue((output_dir / "course_plan.md").exists())
        eval_report_dir = output_dir / "evaluations"
        self.assertTrue(any(eval_report_dir.glob("run-*.jsonl")))
        self.assertIn("[eval] overall=", output)
        self.assertIn("[highlights] saved to", output)

    def test_cli_reports_students_disabled_when_ablation_set(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--ablations", "no_students"])
        self.assertEqual(exit_code, 0)
        self.assertIn("student graders skipped", output)
        self.assertIn("[highlights] saved to", output)
        eval_report = next((output_dir / "evaluations").glob("run-*.jsonl"))
        payload = json.loads(eval_report.read_text().splitlines()[0])
        self.assertFalse(payload["use_students"])
        self.assertEqual(payload["status"], "students_disabled")

    def test_cli_quiet_suppresses_summaries(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--quiet"])
        self.assertEqual(exit_code, 0)
        self.assertTrue((output_dir / "course_plan.md").exists())
        self.assertNotIn("[eval]", output)
        self.assertNotIn("[highlights]", output)
        # Artifacts still exist even when we skip console summaries.
        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("world_model_highlight_artifact", manifest)

    def test_cli_no_world_model_skips_highlight_hint(self) -> None:
        exit_code, output, _ = self._run_cli(["--ablations", "no_world_model"])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("[highlights]", output)


if __name__ == "__main__":
    unittest.main()
