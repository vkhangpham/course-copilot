import json
import tempfile
import unittest
from pathlib import Path

from ccopilot.core.ablation import AblationConfig, parse_ablation_flag
from ccopilot.core.config import (
    CourseConstraints,
    PipelineConfig,
    load_course_constraints,
    load_pipeline_config,
)
from ccopilot.core.provenance import ProvenanceLogger


class ConfigParsingTests(unittest.TestCase):
    def _write_yaml(self, data: str) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml")
        tmp.write(data)
        tmp.flush()
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_load_course_constraints(self) -> None:
        path = self._write_yaml(
            """
            title: DBS PoC
            duration_weeks: 6
            audience:
              persona: grad
              prior_knowledge: ["SQL"]
              goals: ["project"]
            focus_areas: ["transactions"]
            """
        )
        constraints = load_course_constraints(path)
        self.assertIsInstance(constraints, CourseConstraints)
        self.assertEqual(constraints.title, "DBS PoC")
        self.assertEqual(constraints.audience.persona, "grad")

    def test_load_pipeline_config(self) -> None:
        path = self._write_yaml(
            """
            course:
              title: DBS
              duration_weeks: 4
              audience:
                persona: undergrad
            notebook:
              api_base: http://localhost:5055
            world_model:
              schema_path: schema.sql
              dataset_dir: data/handcrafted
            """
        )
        config = load_pipeline_config(path)
        self.assertIsInstance(config, PipelineConfig)
        self.assertEqual(config.notebook.api_base, "http://localhost:5055")
        self.assertTrue(config.world_model.dataset_dir.is_absolute())
        self.assertEqual(config.models.teacher.model, "gpt-5.1")
        self.assertEqual(config.models.ta.model, "gpt-5-mini")
        self.assertEqual(config.models.coder.model, "gpt-5.1-codex-mini")
        self.assertEqual(config.models.student.model, "gpt-5-mini")
        self.assertEqual(config.models.default_temperature, 1.0)
        self.assertEqual(config.models.default_max_tokens, 32000)

    def test_load_pipeline_config_promotes_legacy_model_fields(self) -> None:
        path = self._write_yaml(
            """
            course:
              title: DBS
              duration_weeks: 4
              audience:
                persona: undergrad
            notebook:
              api_base: http://localhost:5055
            world_model:
              schema_path: schema.sql
              dataset_dir: data/handcrafted
            models:
              teacher_model: custom-teacher
              ta_model: custom-ta
              student_model: custom-student
              temperature: 0.42
              max_tokens: 4096
            """
        )
        config = load_pipeline_config(path)

        self.assertEqual(config.models.teacher.model, "custom-teacher")
        self.assertEqual(config.models.ta.model, "custom-ta")
        self.assertEqual(config.models.student.model, "custom-student")
        self.assertEqual(config.models.default_temperature, 0.42)
        self.assertEqual(config.models.default_max_tokens, 4096)


class AblationParsingTests(unittest.TestCase):
    def test_parse_ablation_flag(self) -> None:
        cfg = parse_ablation_flag("no_world_model,no_students")
        self.assertFalse(cfg.use_world_model)
        self.assertFalse(cfg.use_students)
        self.assertTrue(cfg.allow_recursion)

    def test_parse_ablation_flag_empty(self) -> None:
        cfg = parse_ablation_flag(None)
        self.assertEqual(cfg, AblationConfig())


class ProvenanceLoggerTests(unittest.TestCase):
    def test_log_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ProvenanceLogger(Path(tmpdir) / "prov.jsonl")
            event = logger.log(
                {
                    "stage": "unit-test",
                    "message": "ok",
                    "agent": "test",
                }
            )
            self.assertEqual(event.stage, "unit-test")
            contents = (Path(tmpdir) / "prov.jsonl").read_text().strip()
            self.assertTrue(contents)
            data = json.loads(contents)
            self.assertEqual(data["stage"], "unit-test")


if __name__ == "__main__":
    unittest.main()
