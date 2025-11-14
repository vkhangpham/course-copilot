import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest import mock

import yaml

from agents.teacher_rlm import TeacherActionRecord, TeacherRLMRun
from ccopilot.core.config import read_yaml_file
from ccopilot.core.dspy_runtime import DSPyModelHandles
from ccopilot.pipeline import bootstrap_pipeline, run_pipeline
from tests.mocks.notebook_api import NotebookAPIMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeStudentLM:
    def __call__(self, prompt=None, **_kwargs):
        text = prompt or ""
        if "Quiz Question ID" in text:
            return '{"passed": true, "score": 1.0, "answer": "deterministic", "evidence": "quiz coverage"}'
        return '{"overall_score": 0.95, "items": [{"item": "coverage", "passed": true, "score": 0.95, "evidence": "deterministic rubric"}]}'


class PipelineRuntimeTests(unittest.TestCase):
    @staticmethod
    def _section_exports(entries: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if not entries:
            return []
        return [entry for entry in entries if not isinstance(entry, dict) or entry.get("kind") != "preflight"]

    def setUp(self) -> None:
        self._env_backup = {
            key: os.environ.get(key)
            for key in (
                "OPEN_NOTEBOOK_API_BASE",
                "OPEN_NOTEBOOK_API_KEY",
                "OPEN_NOTEBOOK_SLUG",
                "OPEN_NOTEBOOK_EXPORT_DIR",
                "OPEN_NOTEBOOK_EXPORT_MIRROR",
                "COURSEGEN_REPO_ROOT",
            )
        }
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.notebook_api = NotebookAPIMock()
        self.addCleanup(self.notebook_api.close)
        self.config_path = self._write_pipeline_config(
            api_base=self.notebook_api.base_url,
            auth_token=self.notebook_api.token,
        )
        self.output_dir = self.repo_root / "outputs"
        fake_student = FakeStudentLM()
        self._dspy_handles = DSPyModelHandles(teacher=object(), ta=object(), coder=object(), student=fake_student)
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
        self.codeact_patch = mock.patch(
            "apps.orchestrator.teacher.TeacherOrchestrator._run_codeact_program",
            side_effect=self._fake_codeact_program,
        )
        self.addCleanup(self.codeact_patch.stop)
        self.codeact_patch.start()
        self.teacher_run_patch = mock.patch(
            "agents.teacher_rlm.TeacherRLM.run",
            side_effect=self._fake_teacher_run,
        )
        self.addCleanup(self.teacher_run_patch.stop)
        self.teacher_run_patch.start()
        os.environ["OPEN_NOTEBOOK_EXPORT_DIR"] = str(self.repo_root / "notebook_exports")

    def tearDown(self) -> None:
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @staticmethod
    def _fake_codeact_program(name: str, **kwargs):
        if name == "PlanCourse":
            return SimpleNamespace(outline="### Week 1: Deterministic Plan")
        if name == "DraftLectureSection":
            return SimpleNamespace(section="## Draft Section\nContent")
        if name == "EnforceCitations":
            return SimpleNamespace(corrected_section=kwargs.get("md_section"))
        return SimpleNamespace()

    def _fake_teacher_run(self, *, prompt_path: Path, context: Dict[str, Any], tasks: list[Any], **_kwargs):
        actions: list[TeacherActionRecord] = []
        if tasks:
            actions.append(
                TeacherActionRecord(
                    action="spawn_ta",
                    target="SyllabusDesigner",
                    payload=tasks[0].payload,
                    result={"outline": "### Week 1: Deterministic Plan"},
                )
            )
        if len(tasks) > 1:
            actions.append(
                TeacherActionRecord(
                    action="spawn_ta",
                    target="LectureAuthor",
                    payload=tasks[1].payload,
                    result={"section": "## Draft Section\nContent"},
                )
            )
        return TeacherRLMRun(
            mode="simulation",
            prompt_path=prompt_path,
            actions=actions,
            summary="stub",
        )

    def _write_pipeline_config(
        self,
        *,
        api_base: str = "",
        auth_token: str = "test-token",
        filename: str = "pipeline.yaml",
    ) -> Path:
        wm_dir = self.repo_root / "world_model"
        wm_dir.mkdir(parents=True, exist_ok=True)
        schema_path = wm_dir / "schema.sql"
        schema_path.write_text("CREATE TABLE IF NOT EXISTS concepts(id TEXT PRIMARY KEY);\n", encoding="utf-8")

        dataset_dir = self.repo_root / "data" / "handcrafted"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        self._seed_dataset(dataset_dir)
        prompts_dir = self.repo_root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "teacher_seed.txt").write_text("Teacher seed prompt\n", encoding="utf-8")

        eval_dir = self.repo_root / "evals"
        eval_dir.mkdir(parents=True, exist_ok=True)
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

        science_cfg_dir = self.repo_root / "config"
        science_cfg_dir.mkdir(parents=True, exist_ok=True)
        science_cfg_path = science_cfg_dir / "scientific_config.yaml"
        science_cfg_path.write_text("enabled: true\n", encoding="utf-8")
        shutil.copy(PROJECT_ROOT / "config" / "model_config.yaml", science_cfg_dir / "model_config.yaml")

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
  path: "config/model_config.yaml"
notebook:
  api_base: "{api_base}"
  notebook_slug: "test-notebook"
  auth_token: "{auth_token}"
world_model:
  schema_path: "{schema_path}"
  dataset_dir: "{dataset_dir}"
  sqlite_path: "{wm_dir / "state.sqlite"}"
evaluation:
  rubrics_path: "{rubrics_path}"
  quiz_bank_path: "{quiz_bank}"
  max_mutations: 1
"""
        config_path = self.repo_root / filename
        config_path.write_text(config_text.strip(), encoding="utf-8")
        return config_path

    def test_bootstrap_pipeline_uses_canonical_model_config(self) -> None:
        self.mock_configure_dspy.reset_mock()
        ctx = bootstrap_pipeline(config_path=self.config_path, repo_root=self.repo_root)

        self.mock_configure_dspy.assert_called_once()
        (model_cfg,), _ = self.mock_configure_dspy.call_args
        self.assertEqual(model_cfg.teacher.model, "gpt-5.1")
        self.assertEqual(model_cfg.teacher.reasoning, {"effort": "high"})
        self.assertEqual(model_cfg.ta.model, "gpt-5-mini")
        self.assertEqual(model_cfg.coder.model, "gpt-5.1-codex-mini")
        self.assertEqual(model_cfg.student.model, "gpt-5-mini")
        self.assertEqual(model_cfg.default_temperature, 1.0)
        self.assertEqual(model_cfg.default_max_tokens, 32000)
        self.assertIs(ctx.dspy_handles, self._dspy_handles)

    def _seed_dataset(self, dataset_dir: Path) -> None:
        (dataset_dir / "authors.csv").write_text(
            "id,full_name,affiliation\nauthor_a,Author A,Lab\n",
            encoding="utf-8",
        )
        (dataset_dir / "papers.csv").write_text(
            "id,title,venue,year,url,authors\npaper_a,Title,Conf,2024,http://example.com,author_a\n",
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
            'event,year,why_it_matters,related_concepts,citation_id\n"Milestone",2024,"Matters","concept_a","paper_a"\n',
            encoding="utf-8",
        )
        (dataset_dir / "quiz_bank.json").write_text(
            '[{"id": "quiz_a", "learning_objectives": ["concept_a"]}]',
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

    def test_repo_root_overrides_existing_env(self) -> None:
        original_root = os.environ.get("COURSEGEN_REPO_ROOT")
        os.environ["COURSEGEN_REPO_ROOT"] = "/tmp/previous-repo"
        try:
            bootstrap_pipeline(
                config_path=self.config_path,
                repo_root=self.repo_root,
                output_dir=self.output_dir,
            )
            self.assertEqual(Path(os.environ["COURSEGEN_REPO_ROOT"]).resolve(), self.repo_root.resolve())
        finally:
            if original_root is None:
                os.environ.pop("COURSEGEN_REPO_ROOT", None)
            else:
                os.environ["COURSEGEN_REPO_ROOT"] = original_root

    def test_full_run_emits_teacher_artifacts(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        self.assertIs(ctx.dspy_handles, self._dspy_handles)
        with self.notebook_api.patch_open_notebook_client():
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
        self.assertIsNotNone(artifacts.teacher_trace)
        assert artifacts.teacher_trace is not None
        self.assertTrue(artifacts.teacher_trace.exists())
        self.assertIsNotNone(artifacts.notebook_exports)
        self.assertIsNotNone(artifacts.notebook_export_summary)
        self.assertIsNotNone(artifacts.notebook_export_summary)
        self.assertIsNotNone(artifacts.scientific_metrics)
        self.assertIsNotNone(artifacts.scientific_metrics_path)
        self.assertIsNotNone(artifacts.science_config_path)
        assert artifacts.science_config_path is not None
        self.assertTrue(artifacts.science_config_path.exists())
        assert artifacts.scientific_metrics_path is not None
        self.assertTrue(artifacts.scientific_metrics_path.exists())
        science_payload = json.loads(artifacts.scientific_metrics_path.read_text(encoding="utf-8"))
        self.assertIn("metrics", science_payload)
        self.assertIn("pedagogical", science_payload["metrics"])

        plan_text = artifacts.course_plan.read_text(encoding="utf-8")
        self.assertIn("Test Course", plan_text)
        self.assertIn("Concept Highlights", plan_text)
        self.assertIn("concept_a", plan_text)
        self.assertNotIn("Placeholder plan", plan_text)
        self.assertNotIn("CodeAct outline unavailable", plan_text)

        lecture_text = artifacts.lecture.read_text(encoding="utf-8")
        self.assertIn("## Module Overview", lecture_text)
        self.assertIn("## Reading Starter Pack", lecture_text)
        self.assertIn("## Concept Highlights", lecture_text)
        self.assertIn("Concept A", lecture_text)
        self.assertIn("## Timeline Signals", lecture_text)
        self.assertIn("## Suggested Practice", lecture_text)
        self.assertIn("Exercise · Quiz A", lecture_text)
        self.assertIn("## Sources & Citations", lecture_text)
        self.assertNotIn("LectureAuthor TA output unavailable", lecture_text)
        self.assertNotIn("stub", lecture_text.lower())

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

        eval_contents = artifacts.eval_report.read_text(encoding="utf-8").splitlines()
        self.assertTrue(eval_contents)
        parsed = json.loads(eval_contents[0])
        self.assertEqual(parsed.get("rubric_engine"), "llm")
        self.assertEqual(parsed.get("quiz_engine"), "llm")
        self.assertIn("explanations", highlights)
        self.assertEqual(
            manifest.get("world_model_highlight_artifact"),
            str(artifacts.highlights),
        )
        self.assertEqual(manifest.get("highlight_source"), "world_model")
        self.assertEqual(artifacts.highlight_source, "world_model")
        self.assertEqual(manifest.get("teacher_trace"), str(artifacts.teacher_trace))
        teacher_meta = manifest.get("teacher_rlm")
        self.assertIsNotNone(teacher_meta)
        assert teacher_meta is not None
        self.assertEqual(teacher_meta.get("mode"), artifacts.teacher_rlm_mode)
        self.assertIsNone(teacher_meta.get("reason"))
        notebook_exports = manifest.get("notebook_exports")
        self.assertIsNotNone(notebook_exports)
        assert notebook_exports is not None
        preflight_entry = next(
            (entry for entry in notebook_exports if isinstance(entry, dict) and entry.get("kind") == "preflight"),
            None,
        )
        self.assertIsNotNone(preflight_entry)
        sections = self._section_exports(notebook_exports)
        self.assertGreaterEqual(len(sections), 1)
        self.assertIn("response", sections[0])
        self.assertIn("evaluation", manifest)
        self.assertTrue(manifest["evaluation"].get("use_students"))
        self.assertIn("attempts", manifest["evaluation"])
        self.assertIn("attempts", manifest["evaluation"])
        self.assertGreaterEqual(len(self.notebook_api.notes), 1)
        export_response = sections[0]["response"]
        self.assertEqual(export_response.get("status"), "ok")
        self.assertIn("note_id", export_response)

        export_summary = manifest.get("notebook_export_summary")
        self.assertIsNotNone(export_summary)
        assert export_summary is not None
        self.assertGreater(export_summary["success"], 0)
        self.assertEqual(
            manifest.get("scientific_metrics_artifact"),
            str(artifacts.scientific_metrics_path),
        )
        self.assertIn("scientific_metrics", manifest)
        self.assertEqual(
            manifest.get("science_config_path"),
            str(artifacts.science_config_path),
        )

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
        self.assertEqual(
            highlight_payload.get("evaluation_engines"),
            {"rubric": "llm", "quiz": "llm"},
        )

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
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        eval_record = json.loads(artifacts.eval_report.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(eval_record["use_students"])
        self.assertEqual(eval_record["status"], "students_disabled")

    def test_world_model_ablation_uses_dataset_highlights_only(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_world_model",
        )
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        self.assertIsNotNone(artifacts.highlights)
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        highlights = manifest["world_model_highlights"]
        self.assertIsInstance(highlights, dict)
        self.assertIn("syllabus_modules", highlights)
        self.assertNotIn("concepts", highlights)
        self.assertEqual(manifest.get("highlight_source"), "dataset")
        self.assertEqual(artifacts.highlight_source, "dataset")
        self.assertTrue(
            self.notebook_api.notes,
            "Notebook export should still occur when only the world model is disabled",
        )
        provenance_path = ctx.paths.logs_dir / "provenance.jsonl"
        self.assertTrue(provenance_path.exists())
        self.assertNotIn(
            "World-model snapshot missing",
            provenance_path.read_text(encoding="utf-8"),
        )

    def test_recursion_ablation_still_exports_notebook(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_recursion",
        )
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        self.assertTrue(self.notebook_api.notes, "Notebook API should still publish when recursion is disabled")
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        exports = manifest.get("notebook_exports") or []
        self.assertTrue(exports, "Manifest should include notebook export entries")
        reasons = [entry.get("response", {}).get("reason") for entry in exports if isinstance(entry, dict)]
        self.assertNotIn("recursion_disabled", reasons)

    def test_science_config_disable_skips_metrics(self) -> None:
        config_dir = self.repo_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        science_cfg = config_dir / "scientific_config.yaml"
        science_cfg.write_text("enabled: false\n", encoding="utf-8")

        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        self.assertIsNone(artifacts.scientific_metrics)
        self.assertIsNone(artifacts.scientific_metrics_path)
        self.assertEqual(
            str(artifacts.science_config_path),
            str(science_cfg.resolve()),
        )
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        self.assertNotIn("scientific_metrics", manifest)
        self.assertIsNone(manifest.get("scientific_metrics_artifact"))
        self.assertEqual(manifest.get("science_config_path"), str(science_cfg.resolve()))

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
        cfg = read_yaml_file(self.config_path)
        expected_base = cfg.get("notebook", {}).get("api_base") or ""
        expected_slug = cfg.get("notebook", {}).get("notebook_slug") or ""
        expected_key = cfg.get("notebook", {}).get("auth_token")

        if expected_base:
            self.assertEqual(os.environ["OPEN_NOTEBOOK_API_BASE"], expected_base)
        if expected_slug:
            self.assertEqual(os.environ["OPEN_NOTEBOOK_SLUG"], expected_slug)
        if expected_key:
            self.assertEqual(os.environ.get("OPEN_NOTEBOOK_API_KEY"), expected_key)

    def test_world_model_ablation_uses_dataset_outline(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_world_model",
        )
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        self.assertIsNotNone(artifacts.highlights)
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest.get("world_model_highlights"), dict)
        self.assertFalse(manifest.get("world_model_store_exists"))
        self.assertEqual(manifest.get("highlight_source"), "dataset")
        self.assertEqual(artifacts.highlight_source, "dataset")
        plan_text = artifacts.course_plan.read_text(encoding="utf-8")
        self.assertIn("dataset syllabus snapshot", plan_text)

    def test_recursion_ablation_skips_teacher_rlm(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_recursion",
        )
        with mock.patch(
            "agents.teacher_rlm.TeacherRLM.run",
            side_effect=AssertionError("Teacher RLM should not run when recursion is disabled"),
        ):
            with self.notebook_api.patch_open_notebook_client():
                artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        self.assertIsNone(artifacts.teacher_trace)
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        self.assertIsNone(manifest.get("teacher_trace"))

    def test_combined_ablations_enforce_all_toggles(self) -> None:
        ctx = bootstrap_pipeline(
            config_path=self.config_path,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
            ablations="no_world_model,no_students,no_recursion",
        )
        with self.notebook_api.patch_open_notebook_client():
            artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        expected_ablations = {
            "use_world_model": False,
            "use_students": False,
            "allow_recursion": False,
        }
        self.assertEqual(manifest.get("ablations"), expected_ablations)
        self.assertEqual(manifest.get("highlight_source"), "dataset")
        self.assertEqual(artifacts.highlight_source, "dataset")
        self.assertIsNone(manifest.get("teacher_trace"))
        self.assertIsNone(artifacts.teacher_trace)

        eval_record = json.loads(artifacts.eval_report.read_text(encoding="utf-8").splitlines()[0])
        self.assertFalse(eval_record["use_students"])
        self.assertEqual(eval_record["status"], "students_disabled")

        self.assertFalse(manifest.get("world_model_store_exists"))
        self.assertTrue(
            self.notebook_api.notes,
            "Notebook export should remain available even when every ablation is active",
        )

    def test_notebook_export_offline_queue_written(self) -> None:
        offline_config = self._write_pipeline_config(api_base="", filename="pipeline-offline.yaml")
        os.environ.pop("OPEN_NOTEBOOK_API_BASE", None)
        os.environ.pop("OPEN_NOTEBOOK_API_KEY", None)
        ctx = bootstrap_pipeline(
            config_path=offline_config,
            repo_root=self.repo_root,
            output_dir=self.output_dir,
        )
        artifacts = run_pipeline(ctx, dry_run=False)

        assert artifacts is not None
        manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
        exports = manifest.get("notebook_exports")
        self.assertIsNotNone(exports)
        assert exports is not None
        sections = self._section_exports(exports)
        self.assertTrue(sections)
        response = sections[0]["response"]
        self.assertEqual(response.get("status"), "queued")
        export_path = Path(response["export_path"])
        self.assertTrue(export_path.exists())
        self.assertEqual(response.get("notebook"), "test-notebook")

        export_summary = manifest.get("notebook_export_summary")
        self.assertIsNotNone(export_summary)
        assert export_summary is not None
        self.assertGreaterEqual(len(export_summary.get("queued_exports", [])), 1)


if __name__ == "__main__":
    unittest.main()
