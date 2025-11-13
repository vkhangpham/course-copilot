"""Bayesian belief network for world model uncertainty quantification.

This module provides confidence scoring, contradiction detection,
and belief updating for knowledge claims in the world model.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger("coursegen.belief_network")


@dataclass
class BeliefState:
    """Represents belief in a claim with confidence and evidence."""

    claim_id: str
    content: str
    confidence: float  # 0.0 to 1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)  # IDs of contradicting claims
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    update_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "contradictions": self.contradictions,
            "last_updated": self.last_updated.isoformat(),
            "update_history": self.update_history,
        }


class BayesianBeliefNetwork:
    """Manages beliefs and uncertainties in the world model."""

    def __init__(
        self,
        prior_weight: float = 0.3,
        evidence_weight: float = 0.7,
        contradiction_threshold: float = 0.8,
        confidence_decay_rate: float = 0.95,
    ):
        """Initialize belief network.

        Args:
            prior_weight: Weight given to prior beliefs (0-1)
            evidence_weight: Weight given to new evidence (0-1)
            contradiction_threshold: Similarity threshold for contradiction detection
            confidence_decay_rate: Daily decay rate for confidence (0-1)
        """
        self.prior_weight = prior_weight
        self.evidence_weight = evidence_weight
        self.contradiction_threshold = contradiction_threshold
        self.confidence_decay_rate = confidence_decay_rate

        self.beliefs: Dict[str, BeliefState] = {}

    def add_claim(
        self,
        claim_id: str,
        content: str,
        citations: List[str],
        initial_confidence: float = 0.5,
    ) -> BeliefState:
        """Add a new claim to the belief network.

        Args:
            claim_id: Unique claim identifier
            content: Claim content/text
            citations: List of citation IDs supporting the claim
            initial_confidence: Initial confidence score

        Returns:
            BeliefState for the new claim
        """
        # Check for contradictions with existing claims
        contradictions = self.detect_contradictions(content)

        # Adjust initial confidence based on evidence strength
        evidence_strength = self._assess_evidence_strength(citations)
        adjusted_confidence = self._bayesian_update(
            prior=initial_confidence,
            likelihood=evidence_strength,
            evidence_count=len(citations),
        )

        # Create belief state
        belief = BeliefState(
            claim_id=claim_id,
            content=content,
            confidence=adjusted_confidence,
            evidence=[
                {
                    "type": "citation",
                    "citations": citations,
                    "strength": evidence_strength,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            contradictions=contradictions,
        )

        self.beliefs[claim_id] = belief

        # Log if contradictions found
        if contradictions:
            LOGGER.warning(
                f"Claim {claim_id} contradicts existing claims: {contradictions}"
            )
            for contradicting_id in contradictions:
                existing_belief = self.beliefs.get(contradicting_id)
                if existing_belief is not None and claim_id not in existing_belief.contradictions:
                    existing_belief.contradictions.append(claim_id)

        return belief

    def update_belief(
        self,
        claim_id: str,
        new_evidence: Dict[str, Any],
        evidence_type: str = "empirical",
    ) -> BeliefState:
        """Update belief based on new evidence.

        Args:
            claim_id: Claim to update
            new_evidence: New evidence data
            evidence_type: Type of evidence (empirical, theoretical, citation)

        Returns:
            Updated BeliefState
        """
        if claim_id not in self.beliefs:
            raise ValueError(f"Unknown claim: {claim_id}")

        belief = self.beliefs[claim_id]

        # Calculate likelihood from new evidence
        likelihood = self._calculate_likelihood(new_evidence, evidence_type)

        # Bayesian update
        prior = belief.confidence
        posterior = self._bayesian_update(
            prior=prior,
            likelihood=likelihood,
            evidence_count=len(belief.evidence) + 1,
        )

        # Record update
        update_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prior": prior,
            "posterior": posterior,
            "evidence_type": evidence_type,
            "evidence": new_evidence,
        }

        belief.confidence = posterior
        belief.evidence.append(new_evidence)
        belief.update_history.append(update_record)
        belief.last_updated = datetime.now(timezone.utc)

        LOGGER.info(
            f"Updated belief for claim {claim_id}: {prior:.3f} → {posterior:.3f}"
        )

        return belief

    def detect_contradictions(
        self,
        claim_content: str,
        existing_claims: Optional[List[Tuple[str, str]]] = None,
    ) -> List[str]:
        """Detect contradictions with existing claims.

        Args:
            claim_content: Content of new claim
            existing_claims: Optional list of (id, content) tuples to check against

        Returns:
            List of contradicting claim IDs
        """
        contradictions = []

        # If no existing claims provided, check against all beliefs
        if existing_claims is None:
            existing_claims = [
                (belief.claim_id, belief.content)
                for belief in self.beliefs.values()
            ]

        # Check for semantic contradictions
        for claim_id, existing_content in existing_claims:
            if self._are_contradictory(claim_content, existing_content):
                contradictions.append(claim_id)

        return contradictions

    def apply_confidence_decay(
        self,
        days_elapsed: float = 1.0,
    ) -> Dict[str, float]:
        """Apply temporal confidence decay to all beliefs.

        Args:
            days_elapsed: Number of days since last decay

        Returns:
            Dictionary of claim_id -> new_confidence
        """
        updated_confidences = {}

        for claim_id, belief in self.beliefs.items():
            # Apply exponential decay
            decay_factor = self.confidence_decay_rate ** days_elapsed
            new_confidence = belief.confidence * decay_factor

            # Don't decay below a minimum threshold
            new_confidence = max(0.1, new_confidence)

            belief.confidence = new_confidence
            updated_confidences[claim_id] = new_confidence

        LOGGER.info(
            f"Applied confidence decay ({days_elapsed} days) to {len(self.beliefs)} claims"
        )

        return updated_confidences

    def resolve_contradiction(
        self,
        claim_id: str,
        contradicting_id: str,
        resolution_strategy: str = "highest_confidence",
    ) -> Tuple[str, str]:
        """Resolve contradiction between two claims.

        Args:
            claim_id: First claim ID
            contradicting_id: Second claim ID
            resolution_strategy: How to resolve (highest_confidence, most_recent, merge)

        Returns:
            Tuple of (accepted_id, rejected_id)
        """
        if claim_id not in self.beliefs or contradicting_id not in self.beliefs:
            raise ValueError("Both claims must exist in belief network")

        claim1 = self.beliefs[claim_id]
        claim2 = self.beliefs[contradicting_id]

        if resolution_strategy == "highest_confidence":
            if claim1.confidence >= claim2.confidence:
                accepted, rejected = claim_id, contradicting_id
            else:
                accepted, rejected = contradicting_id, claim_id

        elif resolution_strategy == "most_recent":
            if claim1.last_updated >= claim2.last_updated:
                accepted, rejected = claim_id, contradicting_id
            else:
                accepted, rejected = contradicting_id, claim_id

        elif resolution_strategy == "merge":
            # Merge evidence from both claims
            accepted = claim_id
            rejected = contradicting_id

            # Combine evidence
            claim1.evidence.extend(claim2.evidence)

            # Recalculate confidence with combined evidence
            combined_evidence_strength = sum(
                e.get("strength", 0.5) for e in claim1.evidence
            ) / len(claim1.evidence)

            claim1.confidence = self._bayesian_update(
                prior=claim1.confidence,
                likelihood=combined_evidence_strength,
                evidence_count=len(claim1.evidence),
            )

        else:
            raise ValueError(f"Unknown resolution strategy: {resolution_strategy}")

        # Mark rejected claim
        rejected_belief = self.beliefs[rejected]
        rejected_belief.confidence = 0.0

        # Update contradiction lists
        claim1.contradictions = [c for c in claim1.contradictions if c != contradicting_id]
        claim2.contradictions = [c for c in claim2.contradictions if c != claim_id]

        LOGGER.info(
            f"Resolved contradiction: accepted={accepted}, rejected={rejected}, "
            f"strategy={resolution_strategy}"
        )

        return accepted, rejected

    def get_belief_summary(self, claim_id: str) -> Dict[str, Any]:
        """Get summary of belief state for a claim.

        Args:
            claim_id: Claim to summarize

        Returns:
            Summary dictionary
        """
        if claim_id not in self.beliefs:
            return {"error": f"Unknown claim: {claim_id}"}

        belief = self.beliefs[claim_id]

        return {
            "claim_id": claim_id,
            "confidence": belief.confidence,
            "confidence_category": self._categorize_confidence(belief.confidence),
            "evidence_count": len(belief.evidence),
            "contradictions": belief.contradictions,
            "last_updated": belief.last_updated.isoformat(),
            "updates_count": len(belief.update_history),
        }

    def get_high_confidence_claims(
        self,
        min_confidence: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """Get claims with high confidence.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            List of (claim_id, confidence) tuples
        """
        high_confidence = [
            (claim_id, belief.confidence)
            for claim_id, belief in self.beliefs.items()
            if belief.confidence >= min_confidence
        ]

        # Sort by confidence descending
        high_confidence.sort(key=lambda x: x[1], reverse=True)

        return high_confidence

    def get_controversial_claims(
        self,
        max_confidence: float = 0.6,
        min_contradictions: int = 1,
    ) -> List[Tuple[str, float, int]]:
        """Get controversial claims (low confidence or contradictions).

        Args:
            max_confidence: Maximum confidence threshold
            min_contradictions: Minimum number of contradictions

        Returns:
            List of (claim_id, confidence, contradiction_count) tuples
        """
        controversial = [
            (claim_id, belief.confidence, len(belief.contradictions))
            for claim_id, belief in self.beliefs.items()
            if belief.confidence <= max_confidence
            or len(belief.contradictions) >= min_contradictions
        ]

        # Sort by confidence ascending
        controversial.sort(key=lambda x: x[1])

        return controversial

    # Private helper methods

    def _bayesian_update(
        self,
        prior: float,
        likelihood: float,
        evidence_count: int = 1,
    ) -> float:
        """Perform Bayesian belief update.

        Args:
            prior: Prior probability (0-1)
            likelihood: Likelihood of evidence given hypothesis (0-1)
            evidence_count: Number of pieces of evidence

        Returns:
            Posterior probability (0-1)
        """
        # Weight likelihood by evidence count (more evidence = higher impact)
        evidence_strength = min(1.0, evidence_count / 10.0)  # Normalize to 0-1
        weighted_likelihood = (
            likelihood * evidence_strength + 0.5 * (1 - evidence_strength)
        )

        # Calculate marginal probability
        # P(E) = P(E|H) * P(H) + P(E|~H) * P(~H)
        p_evidence = weighted_likelihood * prior + (1 - weighted_likelihood) * (1 - prior)

        # Avoid division by zero
        if p_evidence == 0:
            LOGGER.warning("Zero evidence probability in Bayesian update")
            return prior

        # Calculate posterior
        # P(H|E) = P(E|H) * P(H) / P(E)
        posterior = (weighted_likelihood * prior) / p_evidence

        # Ensure bounds
        posterior = max(0.0, min(1.0, posterior))

        return posterior

    def _assess_evidence_strength(self, citations: List[str]) -> float:
        """Assess strength of evidence from citations.

        Args:
            citations: List of citation IDs

        Returns:
            Evidence strength score (0-1)
        """
        if not citations:
            return 0.3  # Low confidence without citations

        # In production, would check citation quality, venue, year, etc.
        # For now, use simple heuristics:
        # - More citations = stronger evidence (with diminishing returns)
        # - Cap at 0.9 (never absolute certainty)

        strength = min(0.9, 0.5 + (len(citations) * 0.1))

        return strength

    def _calculate_likelihood(
        self,
        evidence: Dict[str, Any],
        evidence_type: str,
    ) -> float:
        """Calculate likelihood of evidence supporting claim.

        Args:
            evidence: Evidence data
            evidence_type: Type of evidence

        Returns:
            Likelihood score (0-1)
        """
        if evidence_type == "empirical":
            # Empirical evidence from student outcomes
            score = evidence.get("score", 0.5)
            sample_size = evidence.get("sample_size", 10)

            # Higher scores and larger samples increase likelihood
            likelihood = score * min(1.0, sample_size / 100)

        elif evidence_type == "theoretical":
            # Theoretical evidence from literature
            paper_count = len(evidence.get("papers", []))
            likelihood = min(0.9, 0.5 + (paper_count * 0.1))

        elif evidence_type == "citation":
            # Citation evidence
            citations = evidence.get("citations", [])
            likelihood = self._assess_evidence_strength(citations)

        else:
            # Unknown evidence type
            likelihood = 0.5

        return likelihood

    def _are_contradictory(
        self,
        claim1: str,
        claim2: str,
    ) -> bool:
        """Check if two claims are contradictory.

        Args:
            claim1: First claim text
            claim2: Second claim text

        Returns:
            True if contradictory
        """
        # Simple heuristic: check for negation words
        negation_indicators = [
            ("increases", "decreases"),
            ("improves", "worsens"),
            ("higher", "lower"),
            ("more", "less"),
            ("positive", "negative"),
            ("better", "worse"),
        ]

        claim1_lower = claim1.lower()
        claim2_lower = claim2.lower()

        # Check if claims have opposite terms
        for pos, neg in negation_indicators:
            if (pos in claim1_lower and neg in claim2_lower) or (
                neg in claim1_lower and pos in claim2_lower
            ):
                # Check if they're about similar concepts
                # (very simple overlap check)
                words1 = set(claim1_lower.split())
                words2 = set(claim2_lower.split())
                overlap = len(words1 & words2) / len(words1 | words2)

                if overlap > self.contradiction_threshold:
                    return True

        return False

    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence level.

        Args:
            confidence: Confidence score (0-1)

        Returns:
            Category string
        """
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "moderate"
        elif confidence >= 0.3:
            return "low"
        else:
            return "very_low"

    def export_beliefs(self) -> Dict[str, Any]:
        """Export all beliefs to dictionary.

        Returns:
            Dictionary of all belief states
        """
        return {
            "beliefs": {
                claim_id: belief.to_dict()
                for claim_id, belief in self.beliefs.items()
            },
            "config": {
                "prior_weight": self.prior_weight,
                "evidence_weight": self.evidence_weight,
                "contradiction_threshold": self.contradiction_threshold,
                "confidence_decay_rate": self.confidence_decay_rate,
            },
            "statistics": {
                "total_claims": len(self.beliefs),
                "high_confidence": len(self.get_high_confidence_claims()),
                "controversial": len(self.get_controversial_claims()),
                "with_contradictions": sum(
                    1 for b in self.beliefs.values() if b.contradictions
                ),
            },
        }


def integrate_with_world_model(
    world_model_adapter: Any,
    belief_network: BayesianBeliefNetwork,
) -> None:
    """Integrate belief network with world model adapter.

    Args:
        world_model_adapter: World model adapter instance
        belief_network: Belief network instance
    """
    # This would modify the world model adapter to:
    # 1. Call belief_network.add_claim() when recording claims
    # 2. Store confidence scores in the database
    # 3. Check for contradictions before adding claims
    # 4. Apply confidence decay periodically

    LOGGER.info("Integrated belief network with world model")


def create_default_belief_network(config: Optional[Dict[str, Any]] = None) -> BayesianBeliefNetwork:
    """Create belief network with default or custom configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured BayesianBeliefNetwork
    """
    if config is None:
        config = {}

    return BayesianBeliefNetwork(
        prior_weight=config.get("prior_weight", 0.3),
        evidence_weight=config.get("evidence_weight", 0.7),
        contradiction_threshold=config.get("contradiction_threshold", 0.8),
        confidence_decay_rate=config.get("confidence_decay_rate", 0.95),
    )
