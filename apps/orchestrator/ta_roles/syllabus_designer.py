"""Role definition for the syllabus designer TA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import yaml


@dataclass
class WeeklyModule:
    week: int
    title: str
    outcomes: List[str]
    readings: List[str]


class SyllabusDesigner:
    """Derive module plans from the taxonomy/world-model inputs."""

    def propose_modules(self, concept_root: Path) -> List[WeeklyModule]:
        dataset_root = concept_root.expanduser().resolve()
        taxonomy = self._load_taxonomy(dataset_root)

        modules = self._modules_from_taxonomy_modules(taxonomy)
        if modules:
            return modules

        modules = self._modules_from_taxonomy_domains(taxonomy)
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

    # ------------------------------------------------------------------

    def _load_taxonomy(self, dataset_root: Path) -> Dict[str, object]:
        taxonomy_path = dataset_root / "taxonomy.yaml"
        if not taxonomy_path.exists():
            return {}
        return self._load_yaml(taxonomy_path)

    def _modules_from_taxonomy_modules(self, taxonomy: Dict[str, object]) -> List[WeeklyModule]:
        modules_payload = taxonomy.get("modules")
        if not isinstance(modules_payload, list):
            return []

        modules: List[WeeklyModule] = []
        for idx, entry in enumerate(modules_payload, start=1):
            if not isinstance(entry, dict):
                continue
            week_number = int(entry.get("week") or idx)
            title = entry.get("title") or entry.get("id") or f"Week {week_number}"
            outcomes = self._string_list(entry.get("learning_objectives") or entry.get("outcomes") or entry.get("focus"))
            if not outcomes and entry.get("focus"):
                outcomes = [str(entry["focus"])]
            readings = self._string_list(entry.get("required_readings") or entry.get("readings"))
            modules.append(
                WeeklyModule(
                    week=week_number,
                    title=title,
                    outcomes=outcomes or ["Review domain concepts"],
                    readings=readings,
                )
            )
        return modules

    def _modules_from_taxonomy_domains(self, taxonomy: Dict[str, object]) -> List[WeeklyModule]:
        domains = taxonomy.get("domains")
        if not isinstance(domains, list):
            return []

        modules: List[WeeklyModule] = []
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
        return modules

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, object]:
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
