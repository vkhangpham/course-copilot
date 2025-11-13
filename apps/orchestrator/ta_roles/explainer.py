"""TA role for writing explanations and worked examples."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import yaml

from .dataset_paths import resolve_dataset_root


@dataclass
class ExplanationChunk:
    heading: str
    body_md: str
    citations: List[str]


class Explainer:
    """Generate lightweight explanation chunks grounded in the handcrafted dataset."""

    def __init__(self, dataset_root: Path | None = None) -> None:
        self.dataset_root = resolve_dataset_root(dataset_root)
        self._concepts = self._load_concepts()
        self._definitions = self._load_definitions()
        self._timeline_by_concept = self._load_timeline()

    def write(self, module: str, *, limit: int = 3) -> List[ExplanationChunk]:
        concepts = self._concepts
        if not concepts:
            return [self._fallback_chunk(module)]

        keywords = self._tokenize(module)
        limit = max(1, limit)
        ranked = sorted(
            concepts.items(),
            key=lambda item: (self._score_concept(item[1], keywords), item[0]),
            reverse=True,
        )

        chunks: List[ExplanationChunk] = []
        for concept_id, concept in ranked[:limit]:
            chunk = self._concept_to_chunk(concept_id, concept)
            if chunk:
                chunks.append(chunk)

        return chunks or [self._fallback_chunk(module)]

    # ------------------------------------------------------------------

    def _concept_to_chunk(self, concept_id: str, concept: Dict[str, object]) -> ExplanationChunk:
        name = str(concept.get("name") or concept_id)
        heading = f"{name} ({concept_id})"
        body_lines: List[str] = []

        summary = str(concept.get("summary") or "").strip()
        if summary:
            body_lines.append(summary)

        definition = self._definitions.get(concept_id)
        if definition:
            definition_text = str(
                definition.get("text")
                or definition.get("definition")
                or definition.get("body")
                or ""
            ).strip()
            if definition_text:
                body_lines.append(f"*Definition.* {definition_text}")

        prereqs = self._string_list(concept.get("prerequisites"))
        if prereqs:
            joined = ", ".join(prereqs[:3]) + ("…" if len(prereqs) > 3 else "")
            body_lines.append(f"*Prerequisites.* {joined}")

        history_line, history_citation = self._history_line(concept_id)
        if history_line:
            body_lines.append(history_line)

        if not body_lines:
            body_lines.append("Explanation forthcoming as the world model expands.")

        citations = self._citations_for(concept, definition)
        if history_citation and history_citation not in citations:
            citations.append(history_citation)

        return ExplanationChunk(
            heading=heading,
            body_md="\n\n".join(body_lines),
            citations=citations,
        )

    def _citations_for(
        self,
        concept: Dict[str, object],
        definition: Dict[str, object] | None,
    ) -> List[str]:
        raw_sources: List[str] = []
        canonical = concept.get("canonical_sources")
        if isinstance(canonical, Sequence):
            raw_sources.extend(str(src) for src in canonical if isinstance(src, str))
        if definition:
            citation = definition.get("citation")
            if isinstance(citation, str):
                raw_sources.append(citation)
        seen = set()
        citations: List[str] = []
        for src in raw_sources:
            if src not in seen:
                seen.add(src)
                citations.append(src)
        return citations

    # ------------------------------------------------------------------

    def _load_concepts(self) -> Dict[str, Dict[str, object]]:
        concepts_path = self.dataset_root / "concepts.yaml"
        if not concepts_path.exists():
            return {}
        payload = self._load_yaml(concepts_path)
        concepts = payload.get("concepts") if isinstance(payload, dict) else None
        if not isinstance(concepts, dict):
            return {}
        return {cid: data for cid, data in concepts.items() if isinstance(data, dict)}

    def _load_definitions(self) -> Dict[str, Dict[str, object]]:
        definitions_path = self.dataset_root / "definitions.yaml"
        if not definitions_path.exists():
            return {}
        payload = self._load_yaml(definitions_path)
        records = payload.get("definitions") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            return {}
        mapping: Dict[str, Dict[str, object]] = {}
        for entry in records:
            if not isinstance(entry, dict):
                continue
            concept_id = entry.get("concept")
            if isinstance(concept_id, str):
                mapping[concept_id] = entry
        return mapping

    def _load_timeline(self) -> Dict[str, List[Dict[str, object]]]:
        timeline_path = self.dataset_root / "timeline.csv"
        if not timeline_path.exists():
            return {}
        events: Dict[str, List[Dict[str, object]]] = {}
        with timeline_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                related_raw = row.get("related_concepts") or row.get("concept_id") or ""
                related = [token.strip() for token in related_raw.split(",") if token.strip()]
                if not related:
                    continue
                event = {
                    "event": row.get("event") or row.get("event_label") or "Timeline event",
                    "year": _safe_int(row.get("year") or row.get("event_year")),
                    "summary": row.get("why_it_matters") or row.get("summary") or "",
                    "citation": row.get("citation_id") or row.get("citation"),
                }
                for concept_id in related:
                    events.setdefault(concept_id, []).append(event)
        for event_list in events.values():
            event_list.sort(key=lambda item: (item.get("year") is None, item.get("year")))
        return events

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        tokens = [token for token in re.split(r"[^a-z0-9]+", text.lower()) if len(token) >= 3]
        return tokens or ["database"]

    def _score_concept(self, concept: Dict[str, object], keywords: Iterable[str]) -> int:
        haystack = " ".join(
            [
                str(concept.get("name") or ""),
                str(concept.get("summary") or ""),
                " ".join(self._string_list(concept.get("tags"))),
            ]
        ).lower()
        score = 0
        for keyword in keywords:
            if keyword and keyword in haystack:
                score += 3
        score += len(self._string_list(concept.get("canonical_sources")))
        return score

    def _fallback_chunk(self, module: str) -> ExplanationChunk:
        module_name = module.strip() or "Course Module"
        return ExplanationChunk(
            heading=f"{module_name} (draft)",
            body_md="Detailed explanations will be generated once the dataset loads."
            "\n\n" "Use the handcrafted assets to seed this section.",
            citations=[],
        )

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            return {}
        return data

    @staticmethod
    def _string_list(values: object) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        if isinstance(values, Sequence):
            return [str(item) for item in values if isinstance(item, str) and item.strip()]
        return []

    def _history_line(self, concept_id: str) -> tuple[str | None, str | None]:
        entries = self._timeline_by_concept.get(concept_id)
        if not entries:
            return None, None
        event = entries[0]
        year = event.get("year")
        summary = (event.get("summary") or "").strip()
        label = event.get("event") or "Milestone"
        if year:
            line = f"*History.* {year}: {label}."
        else:
            line = f"*History.* {label}."
        if summary:
            line = f"{line} {summary}"
        return line, event.get("citation")


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
