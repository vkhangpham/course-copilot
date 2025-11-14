"""TA role for writing exercises/projects."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import yaml

from .dataset_paths import resolve_dataset_root


@dataclass
class Exercise:
    title: str
    description: str
    expected_outcome: str
    difficulty: str = "medium"


class ExerciseAuthor:
    """Generate exercises grounded in the handcrafted quiz bank + concepts."""

    def __init__(self, dataset_root: Path | None = None):
        self.dataset_root = resolve_dataset_root(dataset_root)

    def draft(
        self,
        topics: Sequence[str] | None = None,
        *,
        limit: int | None = None,
    ) -> List[Exercise]:
        quiz_items = self._load_quiz_bank()
        concept_summaries = self._concept_summary_map()
        filter_set = {topic.lower() for topic in (topics or []) if topic}

        exercises: List[Exercise] = []
        for quiz in quiz_items:
            lo_tags = quiz.get("learning_objectives", []) or []
            if filter_set and not filter_set.intersection(tag.lower() for tag in lo_tags):
                continue

            summary_parts = [concept_summaries.get(tag.lower(), "Reinforce core concepts") for tag in lo_tags if isinstance(tag, str)]
            if not summary_parts:
                summary_parts = ["Reinforce core concepts"]

            description = quiz.get("prompt", "Solve the exercise.")
            outcome = "; ".join(summary_parts)
            exercises.append(
                Exercise(
                    title=f"Exercise · {quiz.get('id', 'exercise').replace('_', ' ').title()}",
                    description=description,
                    expected_outcome=outcome,
                    difficulty=quiz.get("difficulty", "medium"),
                )
            )

        if limit is not None and limit >= 0:
            exercises = exercises[:limit]
        return exercises

    # ------------------------------------------------------------------

    def _load_quiz_bank(self) -> List[Dict[str, object]]:
        path = self.dataset_root / "quiz_bank.json"
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def _concept_summary_map(self) -> Dict[str, str]:
        concepts_path = self.dataset_root / "concepts.yaml"
        if not concepts_path.exists():
            return defaultdict(lambda: "Apply the concept in practice")
        data = yaml.safe_load(concepts_path.read_text(encoding="utf-8")) or {}
        concepts = data.get("concepts") if isinstance(data, dict) else None
        if not isinstance(concepts, dict):
            return defaultdict(lambda: "Apply the concept in practice")
        mapping = {
            key.lower(): value.get("summary", "Apply the concept in practice") for key, value in concepts.items() if isinstance(value, dict)
        }
        default_map: Dict[str, str] = defaultdict(lambda: "Apply the concept in practice")
        default_map.update(mapping)
        return default_map
