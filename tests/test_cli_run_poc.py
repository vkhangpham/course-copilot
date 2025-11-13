import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from ccopilot.cli.run_poc import (
    _print_artifact_summary,
    _print_highlight_hint,
    _print_scientific_summary,
    main as cli_main,
)
from tests.mocks.notebook_api import NotebookAPIMock


def yaml_dump(data) -> str:
    return yaml.safe_dump(data, sort_keys=False)


class CLIRunPocTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self._stack = ExitStack()
        self.addCleanup(self._stack.close)
        self.notebook_api = NotebookAPIMock()
        self._stack.callback(self.notebook_api.close)
        self._stack.enter_context(self.notebook_api.patch_open_notebook_client())
        self._prepare_repo()
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = self._openai_key or "test-openai-key"
        self.addCleanup(self._restore_openai_key)
        self._notebook_slug = os.environ.get("OPEN_NOTEBOOK_SLUG")
        self.addCleanup(self._restore_notebook_env)
        self._auto_create_env = os.environ.get("OPEN_NOTEBOOK_AUTO_CREATE")
        self.addCleanup(self._restore_auto_create_env)

    def _restore_openai_key(self) -> None:
        if self._openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self._openai_key

    def _restore_notebook_env(self) -> None:
        if self._notebook_slug is None:
            os.environ.pop("OPEN_NOTEBOOK_SLUG", None)
        else:
            os.environ["OPEN_NOTEBOOK_SLUG"] = self._notebook_slug

    def _restore_auto_create_env(self) -> None:
        if self._auto_create_env is None:
            os.environ.pop("OPEN_NOTEBOOK_AUTO_CREATE", None)
        else:
            os.environ["OPEN_NOTEBOOK_AUTO_CREATE"] = self._auto_create_env

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
  api_base: "{self.notebook_api.base_url}"
  notebook_slug: "cli-test-notebook"
  auth_token: "{self.notebook_api.token}"
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
        self.constraints_path = self.repo_root / "constraints_override.yaml"
        self.constraints_path.write_text(
            yaml_dump(
                {
                    "title": "Alt CLI Course",
                    "description": "Override",
                    "duration_weeks": 5,
                    "focus_areas": ["Transactions"],
                    "tone": "mentor",
                    "audience": {
                        "persona": "Override Persona",
                        "prior_knowledge": ["SQL"],
                        "goals": ["Ship"],
                    },
                    "required_sources": ["paper_a"],
                    "banned_sources": [],
                    "learning_objectives": ["Explain overrides"],
                }
            ),
            encoding="utf-8",
        )

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
        self.assertEqual(manifest.get("highlight_source"), "world_model")
        self.assertIn("scientific_metrics", manifest)
        science_artifact = manifest.get("scientific_metrics_artifact")
        self.assertIsInstance(science_artifact, str)
        science_path = Path(science_artifact)
        self.assertTrue(science_path.exists())
        science_payload = json.loads(science_path.read_text())
        self.assertIn("metrics", science_payload)
        plan_text = (output_dir / "course_plan.md").read_text(encoding="utf-8")
        self.assertIn("Concept Highlights", plan_text)
        self.assertTrue(manifest["evaluation"].get("use_students"))

        eval_report = output_dir / "evaluations"
        report_path = next(eval_report.glob("run-*.jsonl"))
        eval_payload = json.loads(report_path.read_text().splitlines()[0])
        self.assertIn("overall_score", eval_payload)
        self.assertIn("[eval] overall=", output)
        self.assertIn("[highlights] (world_model) saved to", output)
        self.assertIn("[notebook]", output)
        self.assertIn("[science]", output)
        self.assertIn("[artifacts]", output)
        self.assertIn("science=", output)

    def test_cli_reports_artifact_locations(self) -> None:
        exit_code, output, output_dir = self._run_cli()
        self.assertEqual(exit_code, 0)
        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        lecture_path = output_dir / "lectures" / "module_01.md"
        self.assertIn(str(manifest_path.resolve()), output)
        self.assertIn(str(lecture_path.resolve()), output)
        self.assertIn("science=", output)

    def test_cli_no_recursion_skips_teacher_trace_hint(self) -> None:
        exit_code, output, _ = self._run_cli(["--ablations", "no_recursion"])
        self.assertEqual(exit_code, 0)
        self.assertIn("[artifacts]", output)
        self.assertNotIn("[teacher] trace", output)

    def test_cli_dry_run_skips_artifacts(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--dry-run"])
        self.assertEqual(exit_code, 0)
        self.assertFalse((output_dir / "course_plan.md").exists())
        self.assertNotIn("[eval]", output)
        self.assertNotIn("[highlights]", output)
        self.assertNotIn("[science]", output)

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
        self.assertIn("[highlights] (world_model) saved to", output)
        self.assertIn("[notebook]", output)

    def test_cli_reports_students_disabled_when_ablation_set(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--ablations", "no_students"])
        self.assertEqual(exit_code, 0)
        self.assertIn("student graders skipped", output)
        self.assertIn("[highlights] (world_model) saved to", output)
        self.assertIn("[notebook]", output)
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
        self.assertNotIn("[notebook]", output)
        self.assertNotIn("[science]", output)
        self.assertNotIn("[artifacts]", output)
        self.assertNotIn("[teacher]", output)
        # Artifacts still exist even when we skip console summaries.
        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("world_model_highlight_artifact", manifest)

    def test_cli_no_world_model_uses_dataset_highlights(self) -> None:
        exit_code, output, output_dir = self._run_cli(["--ablations", "no_world_model"])
        self.assertEqual(exit_code, 0)
        self.assertIn("[highlights] (dataset) saved to", output)
        self.assertIn("[notebook]", output)

        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        highlight_path = manifest.get("world_model_highlight_artifact")
        self.assertIsInstance(highlight_path, str)
        self.assertEqual(manifest.get("highlight_source"), "dataset")

        highlight_payload = json.loads(Path(highlight_path).read_text())
        highlight_data = highlight_payload["world_model_highlights"]
        self.assertIn("syllabus_modules", highlight_data)
        self.assertNotIn("concepts", highlight_data)

    def test_cli_highlight_hint_mentions_source_without_artifact(self) -> None:
        artifacts = SimpleNamespace(highlights=None, highlight_source="dataset")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _print_highlight_hint(artifacts)
        self.assertIn("[highlights] (dataset) not generated", buffer.getvalue())

    def test_cli_science_config_can_disable_metrics(self) -> None:
        science_cfg = self.repo_root / "config" / "scientific_config.yaml"
        science_cfg.write_text("enabled: false\n", encoding="utf-8")
        exit_code, output, output_dir = self._run_cli()
        self.assertEqual(exit_code, 0)
        self.assertNotIn("[science]", output)
        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text())
        self.assertNotIn("scientific_metrics", manifest)
        self.assertNotIn("scientific_metrics_artifact", manifest)

    def test_cli_scientific_summary_formats_metrics(self) -> None:
        metrics = {
            "pedagogical": {"blooms_alignment": 0.75, "learning_path_coherence": 0.5},
            "content_quality": {"citation_validity": 0.9, "citation_coverage": 0.8},
            "learning_outcomes": {"predicted_retention": 0.6},
        }
        artifacts = SimpleNamespace(scientific_metrics=metrics)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _print_scientific_summary(artifacts)
        output = buffer.getvalue()
        self.assertIn("[science]", output)
        self.assertIn("blooms=0.750", output)
        self.assertIn("coherence=0.500", output)
        self.assertIn("citations=0.900", output)

    def test_artifact_summary_includes_teacher_trace_when_available(self) -> None:
        course_plan = self.repo_root / "outputs" / "course_plan.md"
        lecture = self.repo_root / "outputs" / "lectures" / "module_01.md"
        manifest = self.repo_root / "outputs" / "artifacts" / "run-test-manifest.json"
        eval_report = self.repo_root / "outputs" / "evaluations" / "run-test.jsonl"
        provenance = self.repo_root / "outputs" / "logs" / "run-test.jsonl"
        trace = self.repo_root / "outputs" / "logs" / "teacher-trace-test.json"
        for path in [course_plan, lecture, manifest, eval_report, provenance, trace]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stub", encoding="utf-8")
        artifacts = SimpleNamespace(
            course_plan=course_plan,
            lecture=lecture,
            manifest=manifest,
            eval_report=eval_report,
            provenance=provenance,
            teacher_trace=trace,
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _print_artifact_summary(artifacts)
        text = buffer.getvalue()
        self.assertIn("[artifacts]", text)
        self.assertIn(str(trace.resolve()), text)
        self.assertIn("[teacher] trace saved to", text)

    def test_cli_constraints_override_applied(self) -> None:
        exit_code, _, output_dir = self._run_cli(["--constraints", str(self.constraints_path)])
        self.assertEqual(exit_code, 0)
        plan_text = (output_dir / "course_plan.md").read_text(encoding="utf-8")
        self.assertIn("Alt CLI Course", plan_text)

    def test_cli_concept_alias_overrides_dataset_dir(self) -> None:
        concept_override = self.repo_root / "alt_data" / "database_systems"
        shutil.copytree(self.dataset_dir, concept_override)
        shutil.rmtree(self.dataset_dir)

        exit_code, _, _ = self._run_cli(["--concept", str(concept_override)])
        self.assertEqual(exit_code, 0)

    def test_cli_notebook_override_updates_env(self) -> None:
        exit_code, _, _ = self._run_cli(["--notebook", "custom-slug"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(os.environ.get("OPEN_NOTEBOOK_SLUG"), "custom-slug")

    def test_cli_skip_notebook_create_sets_env_flag(self) -> None:
        exit_code, _, _ = self._run_cli(["--skip-notebook-create"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(os.environ.get("OPEN_NOTEBOOK_AUTO_CREATE"), "0")

    def test_cli_run_outside_repo_uses_dataset_env(self) -> None:
        outside_output = self.repo_root / "outputs" / "outside-full-run"
        if outside_output.exists():
            shutil.rmtree(outside_output)

        args = [
            "--repo-root",
            str(self.repo_root),
            "--config",
            "config/pipeline.yaml",
            "--output-dir",
            str(outside_output),
            "--ablations",
            "no_students",
        ]

        cwd_before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = cli_main(args)
            finally:
                os.chdir(cwd_before)

        try:
            self.assertEqual(exit_code, 0)
            self.assertTrue((outside_output / "course_plan.md").exists())
        finally:
            if outside_output.exists():
                shutil.rmtree(outside_output)

    def test_cli_offline_exports_follow_repo_outputs(self) -> None:
        config_path = self.repo_root / "config" / "pipeline.yaml"
        original = config_path.read_text(encoding="utf-8")
        export_dir = self.repo_root / "outputs" / "notebook_exports"
        if export_dir.exists():
            shutil.rmtree(export_dir)
        previous_export_env = os.environ.pop("OPEN_NOTEBOOK_EXPORT_DIR", None)
        try:
            data = yaml.safe_load(original)
            assert isinstance(data, dict)
            data.setdefault("notebook", {})
            data["notebook"]["api_base"] = ""
            data["notebook"].pop("auth_token", None)
            config_path.write_text(yaml_dump(data), encoding="utf-8")

            args = [
                "--repo-root",
                str(self.repo_root),
                "--config",
                "config/pipeline.yaml",
                "--ablations",
                "no_students",
            ]

            cwd_before = Path.cwd()
            with tempfile.TemporaryDirectory() as tmp_dir:
                os.chdir(tmp_dir)
                try:
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        exit_code = cli_main(args)
                finally:
                    os.chdir(cwd_before)

            self.assertEqual(exit_code, 0)
            self.assertTrue(export_dir.exists())
            configured_dir = os.environ.get("OPEN_NOTEBOOK_EXPORT_DIR")
            assert configured_dir is not None
            self.assertEqual(Path(configured_dir).resolve(), export_dir.resolve())
        finally:
            config_path.write_text(original, encoding="utf-8")
            if previous_export_env is None:
                os.environ.pop("OPEN_NOTEBOOK_EXPORT_DIR", None)
            else:
                os.environ["OPEN_NOTEBOOK_EXPORT_DIR"] = previous_export_env
            if export_dir.exists():
                shutil.rmtree(export_dir)

    def test_cli_loads_dotenv_from_repo_root_when_running_outside(self) -> None:
        env_path = self.repo_root / ".env"
        env_path.write_text(
            "\n".join(
                [
                    "OPENAI_API_KEY=dotenv-openai-key",
                    f"OPEN_NOTEBOOK_API_BASE={self.notebook_api.base_url}",
                    f"OPEN_NOTEBOOK_API_KEY={self.notebook_api.token}",
                    "OPEN_NOTEBOOK_SLUG=dotenv-slug",
                ]
            ),
            encoding="utf-8",
        )

        saved_values = {}
        for var in ("OPENAI_API_KEY", "OPEN_NOTEBOOK_API_BASE", "OPEN_NOTEBOOK_API_KEY", "OPEN_NOTEBOOK_SLUG"):
            saved_values[var] = os.environ.pop(var, None)

        output_dir = self.repo_root / "outputs" / "dotenv-run"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        args = [
            "--repo-root",
            str(self.repo_root),
            "--config",
            "config/pipeline.yaml",
            "--output-dir",
            str(output_dir),
            "--ablations",
            "no_students",
        ]

        cwd_before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = cli_main(args)
            finally:
                os.chdir(cwd_before)

        try:
            self.assertEqual(exit_code, 0)
        finally:
            env_path.unlink(missing_ok=True)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            for var, value in saved_values.items():
                if value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = value

    def test_cli_no_recursion_still_runs_codeact(self) -> None:
        def _fake_program(name: str, **kwargs):
            if name == "PlanCourse":
                return SimpleNamespace(outline="### Week Plan")
            if name == "DraftLectureSection":
                return SimpleNamespace(section="## Draft Section\nBody")
            if name == "EnforceCitations":
                return SimpleNamespace(corrected_section=kwargs.get("md_section"))
            return SimpleNamespace()

        fake_exports = [{"title": "Section", "response": {"id": "note-1"}}]

        with patch("apps.orchestrator.teacher.TeacherOrchestrator._run_codeact_program", side_effect=_fake_program), patch(
            "apps.orchestrator.teacher.TeacherOrchestrator._publish_notebook_sections",
            return_value=fake_exports,
        ):
            exit_code, _, output_dir = self._run_cli(["--ablations", "no_recursion"])
        self.assertEqual(exit_code, 0)
        plan_text = (output_dir / "course_plan.md").read_text(encoding="utf-8")
        self.assertIn("AI-generated Outline (CodeAct)", plan_text)
        manifest_path = next((output_dir / "artifacts").glob("run-*-manifest.json"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(manifest.get("teacher_trace"), "Teacher trace should be skipped when recursion is disabled")
        self.assertEqual(manifest.get("notebook_exports"), fake_exports)

    def test_cli_resolves_relative_paths_against_repo_root(self) -> None:
        cwd_before = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            buffer = io.StringIO()
            args = [
                "--repo-root",
                str(self.repo_root),
                "--config",
                "config/pipeline.yaml",
                "--output-dir",
                "outputs/from-outside",
                "--constraints",
                str(self.constraints_path.relative_to(self.repo_root)),
                "--concept",
                "data/handcrafted/database_systems",
                "--world-model-store",
                "outputs/world_model/state.sqlite",
                "--dry-run",
            ]
            try:
                with redirect_stdout(buffer):
                    exit_code = cli_main(args)
            finally:
                os.chdir(cwd_before)

        self.assertEqual(exit_code, 0)
        expected_output_dir = self.repo_root / "outputs" / "from-outside"
        self.assertTrue(expected_output_dir.exists())

    def test_cli_handles_relative_paths_inside_config(self) -> None:
        config_path = self.repo_root / "config" / "pipeline.yaml"
        original = config_path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(original)
            assert isinstance(data, dict)
            data["world_model"]["schema_path"] = "world_model/schema.sql"
            data["world_model"]["dataset_dir"] = "data/handcrafted/database_systems"
            data["world_model"]["sqlite_path"] = "outputs/world_model/state.sqlite"
            data["evaluation"]["rubrics_path"] = "evals/rubrics.yaml"
            data["evaluation"]["quiz_bank_path"] = "data/handcrafted/database_systems/quiz_bank.json"
            config_path.write_text(yaml_dump(data), encoding="utf-8")

            cwd_before = Path.cwd()
            with tempfile.TemporaryDirectory() as tmp_dir:
                os.chdir(tmp_dir)
                try:
                    exit_code, _, _ = self._run_cli([
                        "--repo-root",
                        str(self.repo_root),
                        "--config",
                        "config/pipeline.yaml",
                        "--dry-run",
                    ])
                finally:
                    os.chdir(cwd_before)

            self.assertEqual(exit_code, 0)
        finally:
            config_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
