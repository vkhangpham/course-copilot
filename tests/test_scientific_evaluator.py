import tempfile
import unittest
from pathlib import Path

from apps.orchestrator.scientific_evaluator import ScientificEvaluator


class ScientificEvaluatorTests(unittest.TestCase):
    def test_evaluator_produces_metrics_for_sample_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"

            plan_path.write_text(
                """# Week 1: Foundations\n\n"
                "Students will define ACID properties, explain transaction logs, and design a capstone demo.\n"
                "# Week 2: Scaling\nAnalyze distributed storage and evaluate trade-offs.\n""",
                encoding="utf-8",
            )
            lecture_path.write_text(
                """## Lecture: Reliable Transactions\n"
                "We recall the ACID guarantees and apply them to failure scenarios.\n"
                "This section cites [Garcia, 2021] and [12] for recovery research.\n"
                "Practice: design a sharded log and justify the checkpoints.\n"
                "Another reference appears as (Stone 2020).\n""",
                encoding="utf-8",
            )

            evaluator = ScientificEvaluator()
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=[
                    "Explain ACID guarantees",
                    "Design recovery workflows",
                ],
            )

            payload = metrics.to_dict()
            self.assertGreater(payload["pedagogical"]["blooms_alignment"], 0)
            self.assertGreater(payload["pedagogical"]["learning_path_coherence"], 0)
            self.assertGreater(payload["content_quality"]["citation_validity"], 0)
            self.assertGreater(payload["learning_outcomes"]["predicted_retention"], 0)

    def test_evaluator_respects_metric_toggles(self) -> None:
        config = {
            "evaluation_metrics": {
                "enabled": True,
                "blooms_taxonomy": False,
                "citation_validity": False,
                "retention_prediction": False,
            }
        }
        evaluator = ScientificEvaluator(config=config)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text("# Week 1\nExplain joins", encoding="utf-8")
            lecture_path.write_text(
                "We explain joins. Cite [Smith, 2024] for proof.",
                encoding="utf-8",
            )
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Explain joins"],
            )
            payload = metrics.to_dict()
            self.assertIsNone(payload["pedagogical"].get("blooms_alignment"))
            self.assertIsNone(payload["content_quality"].get("citation_validity"))
            self.assertIsNone(payload["learning_outcomes"].get("predicted_retention"))
