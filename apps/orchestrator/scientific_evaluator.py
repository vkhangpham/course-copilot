"""Scientific evaluation framework for course generation quality.

Provides multi-dimensional metrics aligned with learning science research.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger("coursegen.scientific_eval")


@dataclass
class BloomsTaxonomyLevel:
    """Bloom's Taxonomy cognitive levels."""

    level: int  # 1-6
    name: str  # Remember, Understand, Apply, Analyze, Evaluate, Create
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.keywords:
            self.keywords = self._default_keywords()

    def _default_keywords(self) -> List[str]:
        """Default keywords for each Bloom's level."""
        level_keywords = {
            1: ["define", "list", "recall", "identify", "name", "state", "recognize"],
            2: ["explain", "describe", "summarize", "interpret", "classify", "compare"],
            3: ["apply", "demonstrate", "implement", "use", "execute", "solve"],
            4: ["analyze", "differentiate", "examine", "investigate", "categorize"],
            5: ["evaluate", "assess", "judge", "critique", "justify", "argue"],
            6: ["create", "design", "construct", "develop", "formulate", "synthesize"],
        }
        return level_keywords.get(self.level, [])


# Bloom's Taxonomy levels
BLOOMS_LEVELS = [
    BloomsTaxonomyLevel(1, "Remember"),
    BloomsTaxonomyLevel(2, "Understand"),
    BloomsTaxonomyLevel(3, "Apply"),
    BloomsTaxonomyLevel(4, "Analyze"),
    BloomsTaxonomyLevel(5, "Evaluate"),
    BloomsTaxonomyLevel(6, "Create"),
]


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for course quality."""

    # Pedagogical metrics
    blooms_alignment_score: float = 0.0
    blooms_distribution: Dict[str, float] = field(default_factory=dict)
    learning_path_coherence: float = 0.0
    concept_coverage_completeness: float = 0.0
    prerequisite_satisfaction_rate: float = 0.0

    # Content quality metrics
    factual_accuracy_score: float = 0.0
    citation_validity_score: float = 0.0
    citation_coverage_rate: float = 0.0
    readability_score: float = 0.0
    information_density: float = 0.0

    # Learning outcome predictions
    predicted_retention_rate: float = 0.0
    predicted_engagement_score: float = 0.0
    difficulty_progression_score: float = 0.0
    cognitive_load_score: float = 0.0

    # Overall scores
    overall_pedagogical_score: float = 0.0
    overall_content_quality: float = 0.0
    overall_predicted_effectiveness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pedagogical": {
                "blooms_alignment": self.blooms_alignment_score,
                "blooms_distribution": self.blooms_distribution,
                "learning_path_coherence": self.learning_path_coherence,
                "concept_coverage": self.concept_coverage_completeness,
                "prerequisite_satisfaction": self.prerequisite_satisfaction_rate,
                "overall": self.overall_pedagogical_score,
            },
            "content_quality": {
                "factual_accuracy": self.factual_accuracy_score,
                "citation_validity": self.citation_validity_score,
                "citation_coverage": self.citation_coverage_rate,
                "readability": self.readability_score,
                "information_density": self.information_density,
                "overall": self.overall_content_quality,
            },
            "learning_outcomes": {
                "predicted_retention": self.predicted_retention_rate,
                "predicted_engagement": self.predicted_engagement_score,
                "difficulty_progression": self.difficulty_progression_score,
                "cognitive_load": self.cognitive_load_score,
                "overall": self.overall_predicted_effectiveness,
            },
        }


class ScientificEvaluator:
    """Multi-dimensional course evaluation aligned with learning science."""

    def __init__(
        self,
        world_model_adapter: Optional[Any] = None,
        citation_validator: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.world_model = world_model_adapter
        self.citation_validator = citation_validator
        self.config = config or {}
        eval_cfg = self.config.get("evaluation_metrics")
        if isinstance(eval_cfg, dict):
            self._metric_flags = eval_cfg
            self._metrics_enabled = bool(eval_cfg.get("enabled", True))
        else:
            self._metric_flags = {}
            self._metrics_enabled = True if eval_cfg is None else bool(eval_cfg)

    def evaluate_course(
        self,
        course_plan_path: Path,
        lecture_paths: List[Path],
        learning_objectives: List[str],
    ) -> EvaluationMetrics:
        """Comprehensive course evaluation.

        Args:
            course_plan_path: Path to course plan markdown
            lecture_paths: Paths to lecture markdown files
            learning_objectives: List of learning objectives

        Returns:
            Comprehensive evaluation metrics
        """
        metrics = EvaluationMetrics()

        # Load content
        course_plan = course_plan_path.read_text() if course_plan_path.exists() else ""
        lectures = [p.read_text() for p in lecture_paths if p.exists()]

        # Pedagogical metrics
        if self._metric_enabled("blooms_taxonomy"):
            metrics.blooms_alignment_score = self.assess_blooms_alignment(
                learning_objectives, lectures
            )
            metrics.blooms_distribution = self.calculate_blooms_distribution(
                learning_objectives, lectures
            )
        else:
            metrics.blooms_alignment_score = None
            metrics.blooms_distribution = {}

        if self._metric_enabled("learning_path_coherence"):
            metrics.learning_path_coherence = self.analyze_learning_path_coherence(
                course_plan, lectures
            )
        else:
            metrics.learning_path_coherence = None

        if self._metric_enabled("concept_coverage"):
            metrics.concept_coverage_completeness = self.measure_concept_coverage(
                course_plan, learning_objectives
            )
        else:
            metrics.concept_coverage_completeness = None

        if self._metric_enabled("prerequisite_satisfaction"):
            metrics.prerequisite_satisfaction_rate = self.check_prerequisite_satisfaction(
                course_plan
            )
        else:
            metrics.prerequisite_satisfaction_rate = None

        # Content quality metrics
        if self._metric_enabled("citation_validity"):
            metrics.citation_validity_score = self.verify_citation_validity(lectures)
        else:
            metrics.citation_validity_score = None

        if self._metric_enabled("citation_coverage"):
            metrics.citation_coverage_rate = self.calculate_citation_coverage(lectures)
        else:
            metrics.citation_coverage_rate = None

        if self._metric_enabled("readability"):
            metrics.readability_score = self.calculate_readability(lectures)
        else:
            metrics.readability_score = None

        if self._metric_enabled("information_density"):
            metrics.information_density = self.calculate_information_density(lectures)
        else:
            metrics.information_density = None

        # Learning outcome predictions
        if self._metric_enabled("difficulty_analysis"):
            metrics.difficulty_progression_score = self.analyze_difficulty_progression(
                course_plan, lectures
            )
        else:
            metrics.difficulty_progression_score = None

        if self._metric_enabled("engagement_prediction"):
            metrics.predicted_engagement_score = self.predict_engagement(
                lectures, metrics
            )
        else:
            metrics.predicted_engagement_score = None

        if self._metric_enabled("retention_prediction"):
            metrics.predicted_retention_rate = self.predict_retention_rate(
                course_plan, lectures, metrics
            )
        else:
            metrics.predicted_retention_rate = None

        if self._metric_enabled("cognitive_load_estimation"):
            metrics.cognitive_load_score = self.estimate_cognitive_load(lectures)
        else:
            metrics.cognitive_load_score = None

        # Calculate overall scores
        metrics.overall_pedagogical_score = self._aggregate_pedagogical_score(metrics)
        metrics.overall_content_quality = self._aggregate_content_quality(metrics)
        metrics.overall_predicted_effectiveness = self._aggregate_effectiveness(metrics)

        return metrics

    def assess_blooms_alignment(
        self,
        learning_objectives: List[str],
        lectures: List[str],
    ) -> float:
        """Assess alignment with Bloom's Taxonomy.

        Args:
            learning_objectives: List of learning objectives
            lectures: List of lecture content

        Returns:
            Alignment score (0-1)
        """
        if not learning_objectives or not lectures:
            return 0.0

        aligned_objectives = 0
        total_objectives = len(learning_objectives)

        for objective in learning_objectives:
            # Detect Bloom's level in objective
            objective_level = self._detect_blooms_level(objective)

            # Check if lectures support this level
            for lecture in lectures:
                lecture_levels = self._extract_blooms_levels_from_content(lecture)

                if objective_level in lecture_levels:
                    aligned_objectives += 1
                    break

        alignment_score = aligned_objectives / total_objectives
        return alignment_score

    def calculate_blooms_distribution(
        self,
        learning_objectives: List[str],
        lectures: List[str],
    ) -> Dict[str, float]:
        """Calculate distribution across Bloom's levels.

        Args:
            learning_objectives: Learning objectives
            lectures: Lecture content

        Returns:
            Distribution of Bloom's levels
        """
        level_counts = {level.name: 0 for level in BLOOMS_LEVELS}
        total_activities = 0

        # Count from objectives
        for objective in learning_objectives:
            level = self._detect_blooms_level(objective)
            if level:
                level_counts[level.name] += 1
                total_activities += 1

        # Count from lecture activities
        for lecture in lectures:
            activities = self._extract_activities(lecture)
            for activity in activities:
                level = self._detect_blooms_level(activity)
                if level:
                    level_counts[level.name] += 1
                    total_activities += 1

        # Normalize
        if total_activities > 0:
            distribution = {
                level: count / total_activities
                for level, count in level_counts.items()
            }
        else:
            distribution = level_counts

        return distribution

    def analyze_learning_path_coherence(
        self,
        course_plan: str,
        lectures: List[str],
    ) -> float:
        """Analyze coherence of learning path.

        Args:
            course_plan: Course plan content
            lectures: Lecture contents

        Returns:
            Coherence score (0-1)
        """
        if not lectures:
            return 0.0

        coherence_factors = []

        # Check sequential concept introduction
        concepts_introduced = set()
        coherence_violations = 0

        for lecture in lectures:
            lecture_concepts = self._extract_concepts(lecture)

            for concept in lecture_concepts:
                # Check if prerequisites are met
                prereqs = self._get_prerequisites(concept)
                missing_prereqs = [p for p in prereqs if p not in concepts_introduced]

                if missing_prereqs:
                    coherence_violations += 1

                concepts_introduced.add(concept)

        # Calculate coherence based on violations
        total_concepts = len(concepts_introduced)
        if total_concepts > 0:
            coherence = 1 - (coherence_violations / total_concepts)
            coherence_factors.append(max(0, coherence))

        # Check narrative flow
        narrative_score = self._assess_narrative_flow(lectures)
        coherence_factors.append(narrative_score)

        # Average coherence factors
        return sum(coherence_factors) / len(coherence_factors) if coherence_factors else 0.0

    def measure_concept_coverage(
        self,
        course_plan: str,
        learning_objectives: List[str],
    ) -> float:
        """Measure concept coverage completeness.

        Args:
            course_plan: Course plan content
            learning_objectives: Learning objectives

        Returns:
            Coverage score (0-1)
        """
        if not learning_objectives:
            return 0.0

        # Extract concepts from objectives
        required_concepts = set()
        for objective in learning_objectives:
            concepts = self._extract_concepts(objective)
            required_concepts.update(concepts)

        # Extract concepts from course plan
        covered_concepts = set(self._extract_concepts(course_plan))

        # Calculate coverage
        if required_concepts:
            coverage = len(required_concepts & covered_concepts) / len(required_concepts)
        else:
            coverage = 1.0

        return coverage

    def check_prerequisite_satisfaction(self, course_plan: str) -> float:
        """Check prerequisite satisfaction rate.

        Args:
            course_plan: Course plan content

        Returns:
            Satisfaction rate (0-1)
        """
        # Extract module ordering from course plan
        modules = self._extract_modules(course_plan)

        if not modules:
            return 1.0

        satisfied = 0
        total_dependencies = 0

        for i, module in enumerate(modules):
            prereqs = self._get_module_prerequisites(module)
            total_dependencies += len(prereqs)

            for prereq in prereqs:
                # Check if prerequisite appears in earlier modules
                for j in range(i):
                    if self._module_covers_concept(modules[j], prereq):
                        satisfied += 1
                        break

        if total_dependencies > 0:
            return satisfied / total_dependencies
        return 1.0

    def verify_citation_validity(self, lectures: List[str]) -> float:
        """Verify citation validity.

        Args:
            lectures: Lecture contents

        Returns:
            Validity score (0-1)
        """
        citations = []
        for lecture in lectures:
            citations.extend(self._extract_citations(lecture))

        if not citations:
            return 0.0

        valid_citations = 0

        for citation in citations:
            if self._is_valid_citation(citation):
                valid_citations += 1

        return valid_citations / len(citations)

    def calculate_citation_coverage(self, lectures: List[str]) -> float:
        """Calculate citation coverage rate.

        Args:
            lectures: Lecture contents

        Returns:
            Coverage rate (0-1)
        """
        total_claims = 0
        cited_claims = 0

        for lecture in lectures:
            # Extract factual claims
            claims = self._extract_factual_claims(lecture)
            total_claims += len(claims)

            # Check which claims have citations
            for claim in claims:
                if self._claim_has_citation(claim, lecture):
                    cited_claims += 1

        if total_claims > 0:
            return cited_claims / total_claims
        return 0.0

    def calculate_readability(self, lectures: List[str]) -> float:
        """Calculate readability score using Flesch-Kincaid.

        Args:
            lectures: Lecture contents

        Returns:
            Readability score (0-1, normalized)
        """
        if not lectures:
            return 0.0

        readability_scores = []

        for lecture in lectures:
            score = self._flesch_kincaid_score(lecture)
            readability_scores.append(score)

        avg_score = sum(readability_scores) / len(readability_scores)

        # Normalize to 0-1 (target: 60-70 for college level)
        # Higher Flesch score = easier to read
        normalized = min(1.0, max(0.0, (avg_score - 30) / 40))

        return normalized

    def calculate_information_density(self, lectures: List[str]) -> float:
        """Calculate information density.

        Args:
            lectures: Lecture contents

        Returns:
            Information density score (0-1)
        """
        if not lectures:
            return 0.0

        densities = []

        for lecture in lectures:
            # Count concepts per 1000 words
            word_count = len(lecture.split())
            concepts = self._extract_concepts(lecture)
            concept_count = len(concepts)

            if word_count > 0:
                density = (concept_count / word_count) * 1000
                # Normalize: optimal density is 5-10 concepts per 1000 words
                normalized_density = min(1.0, density / 10)
                densities.append(normalized_density)

        return sum(densities) / len(densities) if densities else 0.0

    def predict_retention_rate(
        self,
        course_plan: str,
        lectures: List[str],
        metrics: EvaluationMetrics,
    ) -> float:
        """Predict student retention rate.

        Args:
            course_plan: Course plan
            lectures: Lectures
            metrics: Current metrics

        Returns:
            Predicted retention rate (0-1)
        """
        components: List[Tuple[str, Optional[float], float]] = []

        repetition_score = self._assess_spaced_repetition(lectures)
        components.append(("repetition", repetition_score, 0.3))

        components.append(("difficulty_analysis", metrics.difficulty_progression_score, 0.25))
        components.append(("engagement_prediction", metrics.predicted_engagement_score, 0.25))

        inverted_load = None
        if metrics.cognitive_load_score is not None:
            inverted_load = 1 - metrics.cognitive_load_score
        components.append(("cognitive_load_estimation", inverted_load, 0.2))

        return self._weighted_average(components)

    def predict_engagement(
        self,
        lectures: List[str],
        metrics: EvaluationMetrics,
    ) -> float:
        """Predict student engagement.

        Args:
            lectures: Lecture contents
            metrics: Current metrics

        Returns:
            Predicted engagement score (0-1)
        """
        components: List[Tuple[str, Optional[float], float]] = []

        interactive_scores = []
        for lecture in lectures:
            has_examples = bool(re.search(r"(?i)example:", lecture))
            has_exercises = bool(re.search(r"(?i)exercise:|practice:", lecture))
            has_questions = bool(re.search(r"\?", lecture))
            interactive_scores.append(sum([has_examples, has_exercises, has_questions]) / 3)
        if interactive_scores:
            components.append(("activities", sum(interactive_scores) / len(interactive_scores), 0.2))

        components.append(("readability", metrics.readability_score, 0.4))

        if metrics.information_density is not None:
            optimal_density = 1 - abs(0.7 - metrics.information_density)
            components.append(("information_density", optimal_density, 0.4))

        return self._weighted_average(components)

    def analyze_difficulty_progression(
        self,
        course_plan: str,
        lectures: List[str],
    ) -> float:
        """Analyze difficulty progression.

        Args:
            course_plan: Course plan
            lectures: Lectures

        Returns:
            Progression score (0-1, higher is better)
        """
        if len(lectures) < 2:
            return 1.0

        difficulties = []

        for lecture in lectures:
            # Estimate difficulty based on:
            # - Bloom's level
            # - Concept complexity
            # - Prerequisite depth

            blooms = self._extract_blooms_levels_from_content(lecture)
            avg_bloom_level = sum(b.level for b in blooms) / len(blooms) if blooms else 1

            concepts = self._extract_concepts(lecture)
            concept_complexity = len(concepts) / 10  # Normalize

            difficulty = (avg_bloom_level / 6 + concept_complexity) / 2
            difficulties.append(difficulty)

        # Check for gradual progression
        gradients = [difficulties[i+1] - difficulties[i] for i in range(len(difficulties)-1)]

        # Penalize large jumps or regressions
        large_jumps = sum(1 for g in gradients if abs(g) > 0.3)
        regressions = sum(1 for g in gradients if g < -0.1)

        progression_quality = 1 - (large_jumps + regressions * 2) / len(gradients)

        return max(0.0, progression_quality)

    def estimate_cognitive_load(self, lectures: List[str]) -> float:
        """Estimate cognitive load.

        Args:
            lectures: Lecture contents

        Returns:
            Cognitive load score (0-1, lower is better)
        """
        if not lectures:
            return 0.0

        load_scores = []

        for lecture in lectures:
            # Factors contributing to cognitive load
            factors = []

            # Concept density
            concepts = self._extract_concepts(lecture)
            words = len(lecture.split())
            if words > 0:
                density = len(concepts) / (words / 100)  # Per 100 words
                # Optimal: 1-2 concepts per 100 words
                density_load = abs(1.5 - density) / 1.5
                factors.append(density_load)

            # Sentence complexity
            sentences = lecture.split('.')
            if sentences:
                avg_words_per_sentence = words / len(sentences)
                # Optimal: 15-20 words per sentence
                complexity_load = abs(17.5 - avg_words_per_sentence) / 17.5
                factors.append(min(1.0, complexity_load))

            # Number of cross-references
            cross_refs = len(re.findall(r"(?i)see|refer to|as mentioned|recall", lecture))
            ref_load = min(1.0, cross_refs / 10)
            factors.append(ref_load)

            load_scores.append(sum(factors) / len(factors) if factors else 0.5)

        return sum(load_scores) / len(load_scores)

    # Helper methods

    def _metric_enabled(self, name: str, default: bool = True) -> bool:
        if not self._metrics_enabled:
            return False
        flag = self._metric_flags.get(name)
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, dict):
            nested = flag.get("enabled")
            if isinstance(nested, bool):
                return nested
        return default

    def _weighted_average(self, components: List[Tuple[str, Optional[float], float]]) -> float:
        numerator = 0.0
        denominator = 0.0
        for key, value, weight in components:
            if weight <= 0:
                continue
            if key in {
                "repetition",
                "activities",
            }:
                # Synthetic metrics not governed by config
                enabled = True
            else:
                enabled = self._metric_enabled(key)
            if not enabled or value is None:
                continue
            numerator += value * weight
            denominator += weight
        return numerator / denominator if denominator else 0.0

    def _detect_blooms_level(self, text: str) -> Optional[BloomsTaxonomyLevel]:
        """Detect Bloom's level from text."""
        text_lower = text.lower()

        for level in reversed(BLOOMS_LEVELS):  # Check higher levels first
            for keyword in level.keywords:
                if keyword in text_lower:
                    return level

        return None

    def _extract_blooms_levels_from_content(self, content: str) -> List[BloomsTaxonomyLevel]:
        """Extract all Bloom's levels from content."""
        levels = []
        sentences = content.split('.')

        for sentence in sentences:
            level = self._detect_blooms_level(sentence)
            if level:
                levels.append(level)

        return levels

    def _extract_concepts(self, text: str) -> List[str]:
        """Extract concepts from text."""
        # Simple heuristic: capitalized terms and quoted terms
        concepts = set()

        # Capitalized terms (2+ words)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        concepts.update(capitalized)

        # Quoted terms
        quoted = re.findall(r'"([^"]+)"', text)
        concepts.update(quoted)

        # Technical terms (words with specific patterns)
        technical = re.findall(r'\b(?:ACID|SQL|NoSQL|CRUD|API|REST|JSON|XML)\b', text)
        concepts.update(technical)

        return list(concepts)

    def _extract_activities(self, lecture: str) -> List[str]:
        """Extract learning activities from lecture."""
        activities = []

        # Find exercise/practice sections
        exercise_pattern = r"(?i)(?:exercise|practice|activity):\s*(.+?)(?:\n\n|$)"
        activities.extend(re.findall(exercise_pattern, lecture, re.DOTALL))

        return activities

    def _get_prerequisites(self, concept: str) -> List[str]:
        """Get prerequisites for a concept."""
        # This would query the world model in production
        # For now, return empty list
        return []

    def _assess_narrative_flow(self, lectures: List[str]) -> float:
        """Assess narrative flow across lectures."""
        if len(lectures) < 2:
            return 1.0

        # Check for connecting phrases between lectures
        connecting_phrases = [
            "building on", "as we saw", "previously", "next", "following",
            "recall that", "extending", "now that we understand"
        ]

        connections_found = 0
        for lecture in lectures[1:]:  # Skip first lecture
            first_paragraph = lecture.split('\n\n')[0] if '\n\n' in lecture else lecture[:500]
            for phrase in connecting_phrases:
                if phrase in first_paragraph.lower():
                    connections_found += 1
                    break

        return connections_found / (len(lectures) - 1) if len(lectures) > 1 else 1.0

    def _extract_modules(self, course_plan: str) -> List[Dict[str, Any]]:
        """Extract modules from course plan."""
        modules = []

        # Find module headers (e.g., "## Module 1:", "# Week 1:")
        module_pattern = r'(?:##|#)\s*(?:Module|Week|Unit)\s*(\d+)[:\s]*([^\n]+)'
        matches = re.finditer(module_pattern, course_plan)

        for match in matches:
            number, title = match.groups()
            modules.append({
                "number": int(number),
                "title": title.strip(),
                "content": "",  # Would extract section content
            })

        return modules

    def _get_module_prerequisites(self, module: Dict[str, Any]) -> List[str]:
        """Get prerequisites for a module."""
        # Extract from module content or title
        return []

    def _module_covers_concept(self, module: Dict[str, Any], concept: str) -> bool:
        """Check if module covers a concept."""
        return concept.lower() in module.get("title", "").lower()

    def _extract_citations(self, lecture: str) -> List[str]:
        """Extract citations from lecture."""
        citations = []

        # Find citation patterns: [Author, Year], (Author Year), etc.
        patterns = [
            r'\[([A-Za-z\s]+,\s*\d{4})\]',
            r'\(([A-Za-z\s]+\s+\d{4})\)',
            r'\[(\d+)\]',  # Numbered citations
        ]

        for pattern in patterns:
            citations.extend(re.findall(pattern, lecture))

        return citations

    def _is_valid_citation(self, citation: str) -> bool:
        """Check if citation is valid."""
        # Would validate against world model in production
        # For now, check basic format
        return bool(re.search(r'[A-Za-z]+.*\d{4}', citation) or re.search(r'^\d+$', citation))

    def _extract_factual_claims(self, lecture: str) -> List[str]:
        """Extract factual claims from lecture."""
        # Simple heuristic: sentences with definitive statements
        sentences = lecture.split('.')

        claims = []
        claim_indicators = ["is", "are", "was", "were", "has", "have", "provides", "ensures"]

        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in claim_indicators):
                # Exclude questions and examples
                if '?' not in sentence and 'example' not in sentence.lower():
                    claims.append(sentence.strip())

        return claims

    def _claim_has_citation(self, claim: str, lecture: str) -> bool:
        """Check if a claim has a nearby citation."""
        # Find claim position
        claim_pos = lecture.find(claim)
        if claim_pos == -1:
            return False

        # Check for citation within 100 characters after claim
        context = lecture[claim_pos:claim_pos + len(claim) + 100]
        return bool(re.search(r'\[.*?\]|\(.*?\)', context))

    def _flesch_kincaid_score(self, text: str) -> float:
        """Calculate Flesch Reading Ease score."""
        # Count sentences, words, syllables
        sentences = text.split('.')
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)

        words = text.split()
        num_words = len(words)

        # Simple syllable count heuristic
        num_syllables = sum(self._count_syllables(word) for word in words)

        if num_sentences == 0 or num_words == 0:
            return 50.0

        # Flesch Reading Ease formula
        score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)

        # Clamp to 0-100
        return max(0.0, min(100.0, score))

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simple heuristic)."""
        word = word.lower()
        vowels = 'aeiou'
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e'
        if word.endswith('e'):
            syllable_count -= 1

        # Ensure at least one syllable
        return max(1, syllable_count)

    def _assess_spaced_repetition(self, lectures: List[str]) -> float:
        """Assess spaced repetition of concepts."""
        if len(lectures) < 2:
            return 0.5

        # Track concept appearances
        concept_appearances = {}

        for i, lecture in enumerate(lectures):
            concepts = set(self._extract_concepts(lecture))
            for concept in concepts:
                if concept not in concept_appearances:
                    concept_appearances[concept] = []
                concept_appearances[concept].append(i)

        # Calculate repetition quality
        repeated_concepts = [c for c, appearances in concept_appearances.items() if len(appearances) > 1]

        if not repeated_concepts:
            return 0.0

        # Assess spacing quality
        spacing_scores = []
        for concept in repeated_concepts:
            appearances = concept_appearances[concept]
            gaps = [appearances[i+1] - appearances[i] for i in range(len(appearances)-1)]

            # Ideal gap: 1-3 lectures
            ideal_spacing = all(1 <= gap <= 3 for gap in gaps)
            spacing_scores.append(1.0 if ideal_spacing else 0.5)

        return sum(spacing_scores) / len(spacing_scores) if spacing_scores else 0.0

    def _aggregate_pedagogical_score(self, metrics: EvaluationMetrics) -> float:
        components = [
            ("blooms_taxonomy", metrics.blooms_alignment_score, 0.25),
            ("learning_path_coherence", metrics.learning_path_coherence, 0.25),
            ("concept_coverage", metrics.concept_coverage_completeness, 0.25),
            ("prerequisite_satisfaction", metrics.prerequisite_satisfaction_rate, 0.25),
        ]
        return self._weighted_average(components)

    def _aggregate_content_quality(self, metrics: EvaluationMetrics) -> float:
        components = [
            ("citation_validity", metrics.citation_validity_score, 0.3),
            ("citation_coverage", metrics.citation_coverage_rate, 0.3),
            ("readability", metrics.readability_score, 0.2),
            ("information_density", metrics.information_density, 0.2),
        ]
        return self._weighted_average(components)

    def _aggregate_effectiveness(self, metrics: EvaluationMetrics) -> float:
        components = [
            ("retention_prediction", metrics.predicted_retention_rate, 0.3),
            ("engagement_prediction", metrics.predicted_engagement_score, 0.3),
            ("difficulty_analysis", metrics.difficulty_progression_score, 0.2),
            (
                "cognitive_load_estimation",
                (1 - metrics.cognitive_load_score) if metrics.cognitive_load_score is not None else None,
                0.2,
            ),
        ]
        return self._weighted_average(components)
