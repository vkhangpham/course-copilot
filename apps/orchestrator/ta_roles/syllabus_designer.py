"""Role definition for the syllabus designer TA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml


@dataclass
class WeeklyModule:
    week: int
    title: str
    outcomes: List[str]
    readings: List[str]


class SyllabusDesigner:
    """Load structured course outlines from the handcrafted dataset."""

    def propose_modules(self, concept_root: Path) -> List[WeeklyModule]:
        dataset_root = concept_root.expanduser().resolve()
        outline_modules = self._modules_from_outline(dataset_root)
        if outline_modules:
            return outline_modules
        return self._modules_from_taxonomy(dataset_root)

    # ------------------------------------------------------------------

    def _modules_from_outline(self, dataset_root: Path) -> List[WeeklyModule]:
        outline_path = dataset_root / "course_outline.yaml"
        if not outline_path.exists():
            return []

        payload = self._load_yaml(outline_path)
        weeks = payload.get("weeks") if isinstance(payload, dict) else None
        if not isinstance(weeks, list):
            return []

        modules: List[WeeklyModule] = []
        for idx, entry in enumerate(weeks, start=1):
            if not isinstance(entry, dict):
                continue
            week_number = int(entry.get("week") or idx)
            title = entry.get("theme") or entry.get("title") or f"Week {week_number}"
            outcomes = self._string_list(entry.get("learning_objectives") or entry.get("outcomes"))
            readings = self._string_list(entry.get("required_readings") or entry.get("readings"))
            modules.append(
                WeeklyModule(
                    week=week_number,
                    title=title,
                    outcomes=outcomes,
                    readings=readings,
                )
            )
        return modules

    def _modules_from_taxonomy(self, dataset_root: Path) -> List[WeeklyModule]:
        taxonomy_path = dataset_root / "taxonomy.yaml"
        if taxonomy_path.exists():
            payload = self._load_yaml(taxonomy_path)
            domains = payload.get("domains") if isinstance(payload, dict) else None
        else:
            domains = None

        modules: List[WeeklyModule] = []
        if isinstance(domains, list):
            for idx, domain in enumerate(domains, start=1):
                if not isinstance(domain, dict):
                    continue
                title = domain.get("title") or domain.get("id") or f"Module {idx}"
                concepts = self._string_list(domain.get("concepts"))
                outcomes = [f"Apply {concept.replace('_', ' ')}" for concept in concepts[:3]]
                readings = self._string_list(domain.get("required_readings") or domain.get("readings"))
                modules.append(
                    WeeklyModule(
                        week=idx,
                        title=title,
                        outcomes=outcomes or ["Review domain concepts"],
                        readings=readings,
                    )
                )
        if modules:
            return modules
        return [
            WeeklyModule(
                week=1,
                title="Course Foundations",
                outcomes=["Review course constraints", "Survey core concepts"],
                readings=[],
            )
        ]

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            return {}
        return data

    @staticmethod
    def _string_list(values: Iterable[str] | None) -> List[str]:
        if not values:
            return []
        if isinstance(values, str):
            return [values]
        return [str(value) for value in values if isinstance(value, str) and value.strip()]
