"""Shared helpers for loading and validating handcrafted datasets."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml


@dataclass
class HandcraftedDataset:
    dataset_dir: Path
    taxonomy: Dict[str, Any]
    concepts: Dict[str, Dict[str, Any]]
    graph: Dict[str, Any]
    definitions: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    authors: List[Dict[str, Any]]
    quiz_bank: List[Dict[str, Any]]
    course_outline: Dict[str, Any]


def load_dataset(dataset_dir: Path) -> HandcraftedDataset:
    dataset_dir = dataset_dir.resolve()
    if not dataset_dir.exists():
        raise FileNotFoundError(dataset_dir)

    taxonomy = _load_yaml(dataset_dir / "taxonomy.yaml") or {}
    concepts_root = _load_yaml(dataset_dir / "concepts.yaml") or {}
    concepts = concepts_root.get("concepts", {}) if isinstance(concepts_root, dict) else {}
    graph = _load_yaml(dataset_dir / "graph.yaml") or {}
    definitions_root = _load_yaml(dataset_dir / "definitions.yaml") or {}
    definitions = definitions_root.get("definitions", []) if isinstance(definitions_root, dict) else []
    timeline = _load_csv(dataset_dir / "timeline.csv")
    papers = _load_csv(dataset_dir / "papers.csv")
    authors = _load_csv(dataset_dir / "authors.csv")
    quiz_bank = json.loads((dataset_dir / "quiz_bank.json").read_text(encoding="utf-8"))
    course_outline = {}
    outline_path = dataset_dir / "course_outline.yaml"
    if outline_path.exists():
        course_outline = _load_yaml(outline_path)

    return HandcraftedDataset(
        dataset_dir=dataset_dir,
        taxonomy=taxonomy,
        concepts=concepts,
        graph=graph,
        definitions=definitions,
        timeline=timeline,
        papers=papers,
        authors=authors,
        quiz_bank=quiz_bank,
        course_outline=course_outline,
    )


def validate_dataset(dataset: HandcraftedDataset) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    author_ids = _unique_ids(dataset.authors, entity="author", errors=errors)
    paper_ids = _unique_ids(dataset.papers, entity="paper", errors=errors)
    concept_ids = set(dataset.concepts.keys())

    # Validate papers -> authors
    for paper in dataset.papers:
        raw = paper.get("authors") or paper.get("author_ids") or ""
        authors = _split(raw)
        missing = [aid for aid in authors if aid not in author_ids]
        if missing:
            errors.append(
                f"Paper {paper.get('id')} references unknown author IDs: {', '.join(missing)}"
            )

    # Concepts -> canonical sources
    for concept_id, payload in dataset.concepts.items():
        for source_id in payload.get("canonical_sources", []) or []:
            if source_id not in paper_ids:
                errors.append(
                    f"Concept {concept_id} references unknown paper {source_id}"
                )

    # Taxonomy references
    domains = dataset.taxonomy.get("domains", []) if isinstance(dataset.taxonomy, dict) else []
    for domain in domains:
        for concept in domain.get("concepts", []):
            if concept not in concept_ids:
                errors.append(f"Taxonomy domain {domain.get('id')} lists unknown concept {concept}")

    # Graph edges
    edges = dataset.graph.get("edges", []) if isinstance(dataset.graph, dict) else []
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src not in concept_ids:
            errors.append(f"Graph edge source {src} is not a known concept")
        if tgt not in concept_ids:
            errors.append(f"Graph edge target {tgt} is not a known concept")
        missing_citations: set[str] = set()
        for citation in edge.get("citations", []) or []:
            if citation in paper_ids or citation in missing_citations:
                continue
            missing_citations.add(citation)
            errors.append(
                f"Graph edge ({src}->{tgt}) references unknown paper {citation}"
            )

    # Definitions
    for definition in dataset.definitions:
        concept = definition.get("concept")
        if concept not in concept_ids:
            errors.append(f"Definition {definition.get('id')} targets unknown concept {concept}")
        citation = definition.get("citation")
        if citation and citation not in paper_ids:
            errors.append(f"Definition {definition.get('id')} cites unknown paper {citation}")

    # Timeline entries
    for row in dataset.timeline:
        event = row.get("event")
        related = _split(row.get("related_concepts", ""))
        for concept in related:
            if concept not in concept_ids:
                errors.append(f"Timeline event '{event}' references unknown concept {concept}")
        citation = row.get("citation") or row.get("citation_id")
        if citation and citation not in paper_ids:
            errors.append(f"Timeline event '{event}' cites unknown paper {citation}")

    # Quiz bank references
    for quiz in dataset.quiz_bank:
        quiz_id = quiz.get("id")
        for concept in quiz.get("concept_ids", []):
            if concept not in concept_ids:
                errors.append(f"Quiz {quiz_id} references unknown concept {concept}")
        for paper in quiz.get("reference_papers", []):
            if paper not in paper_ids:
                warnings.append(f"Quiz {quiz_id} references unknown paper {paper}")

    # Course outline (if supplied)
    modules = dataset.course_outline.get("weeks", []) if isinstance(dataset.course_outline, dict) else []
    for module in modules:
        module_id = module.get("id") or module.get("week")
        for concept in module.get("concept_ids", []):
            if concept not in concept_ids:
                errors.append(f"Course outline module {module_id} references unknown concept {concept}")
        for paper in module.get("required_readings", []):
            if paper not in paper_ids:
                errors.append(
                    f"Course outline module {module_id} references unknown paper {paper}"
                )

    return errors, warnings


def _load_yaml(path: Path) -> dict | list:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_csv(path: Path, *, required: bool = True) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            has_value = False
            for value in cleaned.values():
                if isinstance(value, str) and value.strip():
                    has_value = True
                    break
                if value not in (None, ""):
                    has_value = True
                    break
            if not has_value:
                continue
            rows.append(cleaned)
        return rows


def _split(raw: str | None) -> list[str]:
    return [token.strip() for token in (raw or "").split(";") if token.strip()]


def _unique_ids(rows: Sequence[dict[str, Any]], *, entity: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for row in rows:
        identifier = row.get("id")
        if not identifier:
            errors.append(f"{entity.title()} row missing id: {row}")
            continue
        if identifier in seen:
            errors.append(f"Duplicate {entity} id detected: {identifier}")
        seen.add(identifier)
    return seen
