import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

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

    def test_metric_toggles_support_dict_enabled_flags(self) -> None:
        config = {
            "evaluation_metrics": {
                "enabled": True,
                "blooms_taxonomy": {"enabled": False},
                "learning_path_coherence": {"enabled": True},
            }
        }
        evaluator = ScientificEvaluator(config=config)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text("# Week 1\nExplain joins", encoding="utf-8")
            lecture_path.write_text("We explain joins.", encoding="utf-8")
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Explain joins"],
            )
            payload = metrics.to_dict()
            self.assertIsNone(payload["pedagogical"].get("blooms_alignment"))
            self.assertIsNotNone(payload["pedagogical"].get("learning_path_coherence"))

    def test_compact_author_year_citations_are_detected(self) -> None:
        evaluator = ScientificEvaluator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text("# Week 1\nCover integrity", encoding="utf-8")
            lecture_path.write_text(
                "Normalization is critical for data integrity [Codd1970].\n"
                "Two-phase locking ensures serializability [GrayReuter1993].\n",
                encoding="utf-8",
            )
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Describe normalization", "Explain concurrency control"],
            )
            assert metrics.citation_validity_score is not None
            assert metrics.citation_coverage_rate is not None
            self.assertGreater(metrics.citation_validity_score, 0)
            self.assertGreater(metrics.citation_coverage_rate, 0)

    def test_prerequisite_satisfaction_detects_covered_dependency(self) -> None:
        evaluator = ScientificEvaluator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text(
                dedent(
                    """
                    ## Module 1: Relational Foundations
                    Covers relational algebra basics.

                    ## Module 2: Transactions
                    Prerequisites: Relational Foundations
                    """
                ),
                encoding="utf-8",
            )
            lecture_path.write_text("Lecture body", encoding="utf-8")
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Explain ACID"],
            )
            self.assertEqual(metrics.prerequisite_satisfaction_rate, 1.0)

    def test_prerequisite_satisfaction_flags_missing_dependency(self) -> None:
        evaluator = ScientificEvaluator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text(
                dedent(
                    """
                    ## Module 1: Relational Foundations
                    Covers relational algebra basics.

                    ## Module 2: Advanced Transactions
                    Prerequisites: Distributed Systems
                    """
                ),
                encoding="utf-8",
            )
            lecture_path.write_text("Lecture body", encoding="utf-8")
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Explain ACID"],
            )
            self.assertIsNotNone(metrics.prerequisite_satisfaction_rate)
            self.assertLess(metrics.prerequisite_satisfaction_rate, 1.0)

    def test_doi_and_url_citations_detected(self) -> None:
        evaluator = ScientificEvaluator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text("## Module 1: Foundations", encoding="utf-8")
            lecture_path.write_text(
                "Latest research is referenced at https://doi.org/10.1145/321 "
                "and https://example.com/paper.pdf to support the claims.",
                encoding="utf-8",
            )
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Describe new research"],
            )
            self.assertGreater(metrics.citation_validity_score or 0, 0)

    def test_multiple_citations_split_by_comma(self) -> None:
        evaluator = ScientificEvaluator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            plan_path = tmp_path / "plan.md"
            lecture_path = tmp_path / "lecture.md"
            plan_path.write_text("## Module 1: Foundations", encoding="utf-8")
            lecture_path.write_text(
                "Normalization is critical for integrity [Codd1970, GrayReuter1993].",
                encoding="utf-8",
            )
            metrics = evaluator.evaluate_course(
                course_plan_path=plan_path,
                lecture_paths=[lecture_path],
                learning_objectives=["Explain ACID"],
            )
            assert metrics.citation_coverage_rate is not None
            self.assertGreaterEqual(metrics.citation_coverage_rate, 1.0)

    def test_cognitive_load_handles_clean_sentence_splits(self) -> None:
        evaluator = ScientificEvaluator()
        lecture = (
            "This sentence keeps roughly eighteen words to stay close to the ideal cadence for comprehension. "
            "Another sentence maintains similar pacing so the average should not spike the load metric."
        )
        score = evaluator.estimate_cognitive_load([lecture])
        self.assertLess(score, 0.5)

    def test_cognitive_load_caps_extreme_density(self) -> None:
        evaluator = ScientificEvaluator()
        lecture = "Normalization " * 200  # absurd density to stress the clamp
        score = evaluator.estimate_cognitive_load([lecture])
        self.assertLessEqual(score, 1.0)

    def test_spaced_repetition_rewards_even_spacing(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Normalization intro explains keys",
            "Transactions overview",
            "Normalization revisited with 3NF",
            "Advanced normalization techniques",
        ]
        score = evaluator._assess_spaced_repetition(lectures)
        self.assertGreater(score, 0.6)

    def test_spaced_repetition_penalizes_sparse_occurrences(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Sharding primer",
            "Transactions overview",
            "Query tuning",
            "Security basics",
            "Sharding deep dive",
        ]
        score = evaluator._assess_spaced_repetition(lectures)
        self.assertLess(score, 0.7)
        self.assertGreater(score, 0.0)

    def test_difficulty_progression_rewards_monotonic_growth(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Introduce tables and keys",
            "Explain normalization theory with proofs",
            "Design distributed transactions with serializability and recovery",
        ]
        score = evaluator.analyze_difficulty_progression("", lectures)
        self.assertGreater(score, 0.8)

    def test_difficulty_progression_handles_short_lectures(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Quick ACID refresher",
            "More ACID context",
        ]
        score = evaluator.analyze_difficulty_progression("", lectures)
        self.assertGreaterEqual(score, 0.5)

    def test_difficulty_progression_penalizes_regressions(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Design a distributed consensus protocol with proofs",
            "Recall basic tables and columns",
            "Dive into concurrency anomalies",
        ]
        score = evaluator.analyze_difficulty_progression("", lectures)
        self.assertLess(score, 0.7)

    def test_spaced_repetition_penalizes_low_coverage_even_with_close_gaps(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Transactions overview",
            "Transactions deep dive",
            "Query tuning",
            "Security basics",
            "Consistency models",
        ]
        score = evaluator._assess_spaced_repetition(lectures)
        self.assertLess(score, 0.7)
        self.assertGreater(score, 0.0)

    def test_spaced_repetition_single_repeat_across_many_lectures_stays_low(self) -> None:
        evaluator = ScientificEvaluator()
        lectures = [
            "Normalization intro",
            "Query tuning",
            "Transactions overview",
            "Security basics",
            "Normalization recap",
            "Sharding primer",
            "Consistency models",
        ]
        score = evaluator._assess_spaced_repetition(lectures)
        self.assertLess(score, 0.2)
        self.assertGreater(score, 0.0)
