"""Hypothesis-driven course generation using hypogenic framework.

This module integrates automated hypothesis generation and testing
for pedagogical strategies in CourseGen.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

LOGGER = logging.getLogger("coursegen.hypothesis")


@dataclass
class PedagogicalHypothesis:
    """Represents a testable hypothesis about course generation strategies."""

    id: str
    content: str
    category: str  # e.g., "content_ordering", "difficulty_progression", "engagement"
    confidence: float = 0.5
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "test_results": self.test_results,
        }


class CourseGenHypothesisGenerator:
    """Generate and test hypotheses for course generation strategies."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        world_model_path: Optional[Path] = None,
    ):
        self.config_path = config_path or Path("config/scientific_config.yaml")
        self.world_model_path = world_model_path
        self.hypotheses: List[PedagogicalHypothesis] = []
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load scientific configuration."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default scientific configuration."""
        return {
            "hypothesis_testing": {
                "enabled": True,
                "method": "hypogenic",
                "num_hypotheses": 20,
                "refinement_iterations": 3,
            },
            "prompt_templates": {
                "pedagogical_observation": """
                Course Structure: ${course_structure}
                Student Performance: ${student_metrics}
                Learning Objectives: ${objectives}
                Observation: Students performed ${performance_level} when ${condition}
                """,
                "hypothesis_generation": """
                Based on educational research and observed patterns, generate ${num_hypotheses}
                testable hypotheses about effective course generation strategies.

                Focus on:
                1. Content ordering and prerequisite management
                2. Difficulty progression and scaffolding
                3. Engagement and retention strategies
                4. Assessment alignment with learning objectives
                5. Cognitive load management

                Format each hypothesis as:
                "If [condition], then [expected outcome] because [theoretical rationale]"
                """,
                "hypothesis_inference": """
                Hypothesis: ${hypothesis}
                Course Data: ${course_data}
                Student Outcomes: ${outcomes}

                Evaluate whether this hypothesis is supported by the data.
                Provide confidence score (0-1) and evidence.
                """,
            },
        }

    def generate_pedagogical_hypotheses(
        self,
        student_data: Optional[Dict[str, Any]] = None,
        literature_path: Optional[Path] = None,
    ) -> List[PedagogicalHypothesis]:
        """Generate hypotheses about effective course generation.

        Args:
            student_data: Historical student performance data
            literature_path: Path to education research papers

        Returns:
            List of testable pedagogical hypotheses
        """
        try:
            # Import hypogenic only when needed
            from hypogenic import BaseTask

            # Create custom task for pedagogical hypotheses
            task = BaseTask(
                config_path=str(self.config_path),
                extract_label=self._extract_pedagogical_insight,
            )

            method = self.config["hypothesis_testing"]["method"]
            num_hypotheses = self.config["hypothesis_testing"]["num_hypotheses"]

            if method == "hypogenic" and student_data:
                # Data-driven hypothesis generation from student performance
                LOGGER.info("Generating data-driven pedagogical hypotheses")
                raw_hypotheses = task.generate_hypotheses(
                    method="hypogenic",
                    num_hypotheses=num_hypotheses,
                    data_source=student_data,
                )
            elif method == "hyporefine" and literature_path:
                # Literature-integrated hypothesis generation
                LOGGER.info("Generating literature-informed pedagogical hypotheses")
                raw_hypotheses = task.generate_hypotheses(
                    method="hyporefine",
                    num_hypotheses=num_hypotheses,
                    literature_path=str(literature_path),
                )
            else:
                # Fallback to manual hypotheses
                LOGGER.warning("Using fallback hypothesis generation")
                raw_hypotheses = self._generate_fallback_hypotheses()

            # Convert to PedagogicalHypothesis objects
            self.hypotheses = self._parse_hypotheses(raw_hypotheses)

        except ImportError:
            LOGGER.warning("hypogenic not installed, using fallback hypotheses")
            self.hypotheses = self._generate_fallback_hypotheses()
        except Exception as e:
            LOGGER.error(f"Hypothesis generation failed: {e}")
            self.hypotheses = self._generate_fallback_hypotheses()

        return self.hypotheses

    def _extract_pedagogical_insight(self, llm_output: str) -> str:
        """Extract pedagogical insight from LLM output."""
        import re

        # Look for structured hypothesis format
        pattern = r"If\s+(.*?),\s+then\s+(.*?)(?:\s+because\s+(.*?))?[.]"
        match = re.search(pattern, llm_output, re.IGNORECASE)

        if match:
            condition, outcome, rationale = match.groups()
            return f"If {condition}, then {outcome}" + (f" because {rationale}" if rationale else "")

        # Fallback to finding any insight pattern
        insight_pattern = r"insight:\s*(.*?)(?:\n|$)"
        match = re.search(insight_pattern, llm_output, re.IGNORECASE)

        if match:
            return match.group(1).strip()

        return llm_output.strip()

    def _parse_hypotheses(self, raw_hypotheses: Any) -> List[PedagogicalHypothesis]:
        """Parse raw hypotheses into structured format."""
        parsed = []

        if isinstance(raw_hypotheses, dict) and "hypotheses" in raw_hypotheses:
            raw_list = raw_hypotheses["hypotheses"]
        elif isinstance(raw_hypotheses, list):
            raw_list = raw_hypotheses
        else:
            raw_list = []

        for i, hyp in enumerate(raw_list):
            if isinstance(hyp, dict):
                content = hyp.get("content", str(hyp))
                category = hyp.get("category", self._infer_category(content))
            else:
                content = str(hyp)
                category = self._infer_category(content)

            parsed.append(
                PedagogicalHypothesis(
                    id=f"hyp_{i:03d}",
                    content=content,
                    category=category,
                    confidence=0.5,  # Initial confidence
                )
            )

        return parsed

    def _infer_category(self, content: str) -> str:
        """Infer hypothesis category from content."""
        content_lower = content.lower()

        if any(term in content_lower for term in ["order", "sequence", "prerequisite", "dependency"]):
            return "content_ordering"
        elif any(term in content_lower for term in ["difficulty", "progression", "scaffold", "complexity"]):
            return "difficulty_progression"
        elif any(term in content_lower for term in ["engage", "motivat", "interest", "attention"]):
            return "engagement"
        elif any(term in content_lower for term in ["assess", "quiz", "test", "evaluat"]):
            return "assessment"
        elif any(term in content_lower for term in ["cognitive", "load", "chunk", "segment"]):
            return "cognitive_load"
        else:
            return "general"

    def _generate_fallback_hypotheses(self) -> List[PedagogicalHypothesis]:
        """Generate default hypotheses when hypogenic is unavailable.

        Returns:
            List of PedagogicalHypothesis objects
        """
        fallback_data = [
            {
                "content": (
                    "If concepts are ordered by prerequisite dependencies, "
                    "then students will show better comprehension because they build on prior knowledge"
                ),
                "category": "content_ordering",
            },
            {
                "content": (
                    "If difficulty increases gradually with explicit scaffolding, "
                    "then retention rates will improve because cognitive load is managed"
                ),
                "category": "difficulty_progression",
            },
            {
                "content": "If lectures include real-world examples, then engagement scores will increase because relevance is established",
                "category": "engagement",
            },
            {
                "content": "If assessments align with Bloom's taxonomy levels, then learning outcomes will be more accurately measured",
                "category": "assessment",
            },
            {
                "content": "If content is chunked into 5-7 concept groups, then cognitive load will be optimized for working memory",
                "category": "cognitive_load",
            },
        ]

        # Convert dicts to PedagogicalHypothesis objects
        return [
            PedagogicalHypothesis(
                id=f"fallback_{i:03d}",
                content=h["content"],
                category=h["category"],
                confidence=0.5,
            )
            for i, h in enumerate(fallback_data)
        ]

    def test_hypothesis(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test a hypothesis against course and student data.

        Args:
            hypothesis: Hypothesis to test
            course_data: Generated course structure and content
            student_outcomes: Student performance metrics

        Returns:
            Test results with confidence update
        """
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "confidence_change": 0.0,
            "evidence": [],
        }

        # Category-specific testing logic
        if hypothesis.category == "content_ordering":
            results = self._test_content_ordering(hypothesis, course_data, student_outcomes)
        elif hypothesis.category == "difficulty_progression":
            results = self._test_difficulty_progression(hypothesis, course_data, student_outcomes)
        elif hypothesis.category == "engagement":
            results = self._test_engagement(hypothesis, course_data, student_outcomes)
        elif hypothesis.category == "assessment":
            results = self._test_assessment_alignment(hypothesis, course_data, student_outcomes)
        elif hypothesis.category == "cognitive_load":
            results = self._test_cognitive_load(hypothesis, course_data, student_outcomes)
        else:
            # Generic testing
            results = self._test_generic(hypothesis, course_data, student_outcomes)

        # Update hypothesis confidence based on results
        hypothesis.test_results = results
        hypothesis.confidence = self._bayesian_update(
            prior=hypothesis.confidence,
            likelihood=results.get("likelihood", 0.5),
            evidence_strength=len(results.get("evidence", [])) / 10,  # Normalize by expected evidence
        )

        return results

    def _bayesian_update(
        self,
        prior: float,
        likelihood: float,
        evidence_strength: float,
    ) -> float:
        """Update confidence using Bayesian inference.

        Args:
            prior: Prior confidence (0-1)
            likelihood: Likelihood of evidence given hypothesis (0-1)
            evidence_strength: Strength of evidence (0-1)

        Returns:
            Posterior confidence
        """
        # Simple Bayesian update
        # P(H|E) = P(E|H) * P(H) / P(E)
        # Where P(E) = P(E|H) * P(H) + P(E|~H) * P(~H)

        # Adjust likelihood by evidence strength
        adjusted_likelihood = likelihood * evidence_strength + 0.5 * (1 - evidence_strength)

        # Calculate marginal probability
        p_evidence = adjusted_likelihood * prior + (1 - adjusted_likelihood) * (1 - prior)

        # Avoid division by zero
        if p_evidence == 0:
            LOGGER.warning(
                f"Zero evidence probability in Bayesian update: "
                f"prior={prior:.3f}, likelihood={likelihood:.3f}, evidence_strength={evidence_strength:.3f}"
            )
            return prior

        # Calculate posterior
        posterior = (adjusted_likelihood * prior) / p_evidence

        # Ensure bounds
        posterior = max(0.0, min(1.0, posterior))

        # Log significant updates
        if abs(posterior - prior) > 0.1:
            LOGGER.debug(
                f"Significant belief update: {prior:.3f} → {posterior:.3f} (likelihood={likelihood:.3f}, evidence={evidence_strength:.3f})"
            )

        return posterior

    def _test_content_ordering(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test content ordering hypotheses.

        Args:
            hypothesis: Hypothesis to test
            course_data: Course structure (may contain 'modules', 'lectures', etc.)
            student_outcomes: Student performance metrics

        Returns:
            Test results with support verdict
        """
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Defensive: check if course_data has expected structure
        if not isinstance(course_data, dict):
            LOGGER.warning(f"Invalid course_data type: {type(course_data)}")
            return results

        # Check if prerequisites are properly ordered
        if "modules" in course_data:
            prerequisite_violations = 0
            total_dependencies = 0

            for module in course_data["modules"]:
                if "prerequisites" in module:
                    total_dependencies += len(module["prerequisites"])
                    for prereq in module["prerequisites"]:
                        # Check if prerequisite appears before current module
                        if not self._is_prerequisite_satisfied(prereq, module, course_data):
                            prerequisite_violations += 1

            if total_dependencies > 0:
                satisfaction_rate = 1 - (prerequisite_violations / total_dependencies)
                results["evidence"].append(
                    {
                        "type": "prerequisite_satisfaction",
                        "rate": satisfaction_rate,
                    }
                )

                # Check correlation with student performance
                if "comprehension_score" in student_outcomes:
                    if satisfaction_rate > 0.8 and student_outcomes["comprehension_score"] > 0.7:
                        results["supported"] = True
                        results["likelihood"] = 0.8

        return results

    def _test_difficulty_progression(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test difficulty progression hypotheses."""
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Analyze difficulty curve
        if "modules" in course_data:
            difficulties = [m.get("difficulty", 0.5) for m in course_data["modules"]]

            if len(difficulties) > 1:
                # Calculate difficulty progression smoothness
                gradients = [difficulties[i + 1] - difficulties[i] for i in range(len(difficulties) - 1)]
                avg_gradient = sum(gradients) / len(gradients)
                gradient_variance = sum((g - avg_gradient) ** 2 for g in gradients) / len(gradients)

                results["evidence"].append(
                    {
                        "type": "difficulty_gradient",
                        "average": avg_gradient,
                        "variance": gradient_variance,
                    }
                )

                # Check if gradual progression correlates with retention
                if gradient_variance < 0.1 and "retention_rate" in student_outcomes:
                    if student_outcomes["retention_rate"] > 0.75:
                        results["supported"] = True
                        results["likelihood"] = 0.75

        return results

    def _test_engagement(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test engagement hypotheses."""
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Check for engagement features
        engagement_features = 0
        total_features = 5  # Examples, activities, discussions, projects, multimedia

        if "lectures" in course_data:
            for lecture in course_data["lectures"]:
                if "examples" in lecture and lecture["examples"]:
                    engagement_features += 1
                if "activities" in lecture and lecture["activities"]:
                    engagement_features += 1
                if "discussion_prompts" in lecture:
                    engagement_features += 1
                break  # Check first lecture as sample

        feature_rate = engagement_features / total_features
        results["evidence"].append(
            {
                "type": "engagement_features",
                "rate": feature_rate,
            }
        )

        # Check correlation with engagement metrics
        if feature_rate > 0.6 and "engagement_score" in student_outcomes:
            if student_outcomes["engagement_score"] > 0.7:
                results["supported"] = True
                results["likelihood"] = 0.7

        return results

    def _test_assessment_alignment(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test assessment alignment hypotheses."""
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Check Bloom's taxonomy alignment
        if "assessments" in course_data and "learning_objectives" in course_data:
            aligned_assessments = 0
            total_assessments = len(course_data["assessments"])

            for assessment in course_data["assessments"]:
                if "bloom_level" in assessment:
                    # Check if assessment level matches objective levels
                    for objective in course_data["learning_objectives"]:
                        if objective.get("bloom_level") == assessment["bloom_level"]:
                            aligned_assessments += 1
                            break

            if total_assessments > 0:
                alignment_rate = aligned_assessments / total_assessments
                results["evidence"].append(
                    {
                        "type": "bloom_alignment",
                        "rate": alignment_rate,
                    }
                )

                if alignment_rate > 0.7 and "learning_outcome_achievement" in student_outcomes:
                    if student_outcomes["learning_outcome_achievement"] > 0.75:
                        results["supported"] = True
                        results["likelihood"] = 0.75

        return results

    def _test_cognitive_load(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test cognitive load hypotheses."""
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Check content chunking
        if "modules" in course_data:
            chunk_sizes = []
            for module in course_data["modules"]:
                if "concepts" in module:
                    chunk_sizes.append(len(module["concepts"]))

            if chunk_sizes:
                avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
                optimal_range = (5, 7)  # Miller's magic number

                is_optimal = optimal_range[0] <= avg_chunk_size <= optimal_range[1]
                results["evidence"].append(
                    {
                        "type": "chunk_size",
                        "average": avg_chunk_size,
                        "optimal": is_optimal,
                    }
                )

                if is_optimal and "cognitive_load_score" in student_outcomes:
                    if student_outcomes["cognitive_load_score"] < 0.7:  # Lower is better
                        results["supported"] = True
                        results["likelihood"] = 0.7

        return results

    def _test_generic(
        self,
        hypothesis: PedagogicalHypothesis,
        course_data: Dict[str, Any],
        student_outcomes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generic hypothesis testing."""
        results = {
            "hypothesis_id": hypothesis.id,
            "supported": False,
            "likelihood": 0.5,
            "evidence": [],
        }

        # Simple correlation check
        if "overall_score" in student_outcomes:
            if student_outcomes["overall_score"] > 0.7:
                results["supported"] = True
                results["likelihood"] = 0.6
                results["evidence"].append(
                    {
                        "type": "overall_performance",
                        "score": student_outcomes["overall_score"],
                    }
                )

        return results

    def _is_prerequisite_satisfied(
        self,
        prereq: str,
        module: Dict[str, Any],
        course_data: Dict[str, Any],
    ) -> bool:
        """Check if prerequisite appears before module."""
        module_index = -1
        prereq_index = -1

        for i, m in enumerate(course_data.get("modules", [])):
            if m.get("id") == module.get("id"):
                module_index = i
            if m.get("id") == prereq or prereq in m.get("concepts", []):
                prereq_index = i

        return prereq_index >= 0 and prereq_index < module_index

    def save_hypotheses(self, output_path: Path) -> None:
        """Save hypotheses to file.

        Args:
            output_path: Path to save hypothesis bank
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        hypothesis_bank = {
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "config": self.config,
            "categories": list(set(h.category for h in self.hypotheses)),
        }

        with open(output_path, "w") as f:
            json.dump(hypothesis_bank, f, indent=2)

        LOGGER.info(f"Saved {len(self.hypotheses)} hypotheses to {output_path}")

    def load_hypotheses(self, input_path: Path) -> List[PedagogicalHypothesis]:
        """Load hypotheses from file.

        Args:
            input_path: Path to hypothesis bank

        Returns:
            List of loaded hypotheses
        """
        with open(input_path, "r") as f:
            data = json.load(f)

        self.hypotheses = []
        for h_dict in data.get("hypotheses", []):
            self.hypotheses.append(
                PedagogicalHypothesis(
                    id=h_dict["id"],
                    content=h_dict["content"],
                    category=h_dict["category"],
                    confidence=h_dict.get("confidence", 0.5),
                    evidence=h_dict.get("evidence", []),
                    test_results=h_dict.get("test_results", {}),
                )
            )

        LOGGER.info(f"Loaded {len(self.hypotheses)} hypotheses from {input_path}")
        return self.hypotheses

    def refine_hypotheses(
        self,
        test_results: List[Dict[str, Any]],
        max_iterations: int = 3,
    ) -> List[PedagogicalHypothesis]:
        """Refine hypotheses based on test results.

        Args:
            test_results: Results from hypothesis testing
            max_iterations: Maximum refinement iterations

        Returns:
            Refined hypotheses
        """
        for iteration in range(max_iterations):
            LOGGER.info(f"Refinement iteration {iteration + 1}/{max_iterations}")

            # Sort by confidence
            self.hypotheses.sort(key=lambda h: h.confidence, reverse=True)

            # Keep top performers, replace bottom performers
            cutoff = len(self.hypotheses) // 2
            top_hypotheses = self.hypotheses[:cutoff]

            # Generate new hypotheses based on successful patterns
            new_hypotheses = self._generate_refined_hypotheses(top_hypotheses)

            self.hypotheses = top_hypotheses + new_hypotheses

        return self.hypotheses

    def _generate_refined_hypotheses(
        self,
        successful_hypotheses: List[PedagogicalHypothesis],
    ) -> List[PedagogicalHypothesis]:
        """Generate refined hypotheses based on successful patterns.

        Args:
            successful_hypotheses: High-confidence hypotheses

        Returns:
            New refined hypotheses
        """
        refined = []

        # Extract patterns from successful hypotheses
        patterns = {}
        for hyp in successful_hypotheses:
            if hyp.category not in patterns:
                patterns[hyp.category] = []
            patterns[hyp.category].append(hyp.content)

        # Generate variations
        for category, contents in patterns.items():
            # Create hypothesis that combines successful elements
            if len(contents) >= 2:
                combined = (
                    f"If {self._extract_condition(contents[0])} and {self._extract_condition(contents[1])}, "
                    f"then enhanced {self._extract_outcome(contents[0])}"
                )

                refined.append(
                    PedagogicalHypothesis(
                        id=f"hyp_ref_{len(refined):03d}",
                        content=combined,
                        category=category,
                        confidence=0.6,  # Higher initial confidence for refined
                    )
                )

        return refined

    def _extract_condition(self, hypothesis_content: str) -> str:
        """Extract condition from hypothesis."""
        import re

        match = re.search(r"If\s+(.*?),\s+then", hypothesis_content, re.IGNORECASE)
        return match.group(1) if match else "condition"

    def _extract_outcome(self, hypothesis_content: str) -> str:
        """Extract expected outcome from hypothesis."""
        import re

        match = re.search(r"then\s+(.*?)(?:\s+because|$)", hypothesis_content, re.IGNORECASE)
        return match.group(1) if match else "outcome"


def integrate_with_teacher(
    hypothesis_generator: CourseGenHypothesisGenerator,
    teacher_orchestrator: Any,
) -> Dict[str, Any]:
    """Integrate hypothesis testing with teacher orchestrator.

    Args:
        hypothesis_generator: Hypothesis generator instance
        teacher_orchestrator: Teacher orchestrator instance

    Returns:
        Integration results
    """
    results = {
        "hypotheses_tested": 0,
        "successful_strategies": [],
        "failed_strategies": [],
        "recommendations": [],
    }

    # Generate initial hypotheses
    hypotheses = hypothesis_generator.generate_pedagogical_hypotheses()

    for hypothesis in hypotheses:
        # Apply hypothesis to course generation
        {
            "hypothesis_id": hypothesis.id,
            "config_overrides": _hypothesis_to_config(hypothesis),
        }

        # Generate course with strategy
        # Note: This would integrate with actual teacher orchestrator
        # course_artifacts = teacher_orchestrator.run_with_strategy(strategy)

        # Test hypothesis against outcomes
        # test_results = hypothesis_generator.test_hypothesis(
        #     hypothesis,
        #     course_artifacts.course_data,
        #     course_artifacts.student_outcomes
        # )

        # Track results
        results["hypotheses_tested"] += 1
        # if test_results["supported"]:
        #     results["successful_strategies"].append(strategy)
        # else:
        #     results["failed_strategies"].append(strategy)

    # Generate recommendations
    results["recommendations"] = _generate_recommendations(
        results["successful_strategies"],
        results["failed_strategies"],
    )

    return results


def _hypothesis_to_config(hypothesis: PedagogicalHypothesis) -> Dict[str, Any]:
    """Convert hypothesis to configuration overrides.

    Args:
        hypothesis: Pedagogical hypothesis

    Returns:
        Configuration overrides
    """
    config = {}

    if hypothesis.category == "content_ordering":
        config["enforce_prerequisites"] = True
        config["prerequisite_strategy"] = "strict"
    elif hypothesis.category == "difficulty_progression":
        config["difficulty_curve"] = "gradual"
        config["scaffolding_enabled"] = True
    elif hypothesis.category == "engagement":
        config["include_examples"] = True
        config["interactive_elements"] = True
    elif hypothesis.category == "assessment":
        config["align_with_blooms"] = True
        config["assessment_strategy"] = "formative"
    elif hypothesis.category == "cognitive_load":
        config["chunk_size"] = 6  # Optimal for working memory
        config["concept_grouping"] = "hierarchical"

    return config


def _generate_recommendations(
    successful_strategies: List[Dict[str, Any]],
    failed_strategies: List[Dict[str, Any]],
) -> List[str]:
    """Generate recommendations based on hypothesis testing.

    Args:
        successful_strategies: Strategies that worked
        failed_strategies: Strategies that didn't work

    Returns:
        List of recommendations
    """
    recommendations = []

    if successful_strategies:
        recommendations.append(f"Adopt {len(successful_strategies)} validated strategies for course generation")

    if failed_strategies:
        recommendations.append(f"Avoid {len(failed_strategies)} strategies that showed poor outcomes")

    # Category-specific recommendations
    successful_categories = set()
    for strategy in successful_strategies:
        # Extract category from strategy
        # successful_categories.add(strategy.get("category"))
        pass

    if "content_ordering" in successful_categories:
        recommendations.append("Prioritize prerequisite-based content ordering")

    if "difficulty_progression" in successful_categories:
        recommendations.append("Implement gradual difficulty progression with scaffolding")

    if "engagement" in successful_categories:
        recommendations.append("Include real-world examples and interactive elements")

    return recommendations
