"""Wrapper functions that expose the world-model store to CodeAct."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from world_model.adapters import WorldModelAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE = (PROJECT_ROOT / "outputs" / "world_model" / "state.sqlite").resolve()
STORE_ENV_VAR = "WORLD_MODEL_STORE"


def _adapter(store_path: Path | str | None = None) -> WorldModelAdapter:
    resolved = Path(store_path or os.environ.get(STORE_ENV_VAR, DEFAULT_STORE))
    return WorldModelAdapter(resolved)


def fetch_concepts(
    topic: str | None = None,
    *,
    depth: int = 1,
    limit: int | None = 50,
    store_path: Path | None = None,
) -> list[dict[str, Any]]:
    return _adapter(store_path).fetch_concept_tree(topic=topic, max_depth=depth, limit=limit)


def search_events(
    *,
    query: str | None = None,
    concept_id: str | None = None,
    limit: int = 25,
    store_path: Path | None = None,
) -> list[dict[str, Any]]:
    return _adapter(store_path).search_timeline(query=query, concept_id=concept_id, limit=limit)


def lookup_paper(paper_id: str, *, store_path: Path | None = None) -> dict[str, Any]:
    paper = _adapter(store_path).lookup_paper(paper_id)
    if not paper:
        raise ValueError(f"Unknown paper id: {paper_id}")
    return paper


def record_claim(
    *,
    subject: str,
    content: str,
    citation: str | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    return _adapter(store_path).record_claim(subject=subject, content=content, citation=citation)


def list_claims(
    *,
    subject_id: str | None = None,
    limit: int = 25,
    store_path: Path | None = None,
) -> list[dict[str, Any]]:
    return _adapter(store_path).list_claims(subject_id=subject_id, limit=limit)


def list_relationships(
    *,
    source_id: str | None = None,
    target_id: str | None = None,
    relation_type: str | None = None,
    limit: int = 50,
    store_path: Path | None = None,
) -> list[dict[str, Any]]:
    return _adapter(store_path).list_relationships(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        limit=limit,
    )


def link_concepts(
    *,
    source_id: str,
    target_id: str,
    relation_type: str,
    justification: str | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    return _adapter(store_path).link_concepts(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        justification=justification,
    )


def append_timeline_event(
    *,
    event_label: str,
    related_concept: str,
    summary: str | None = None,
    event_year: int | None = None,
    citation: str | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    return _adapter(store_path).append_timeline_event(
        event_label=event_label,
        related_concept=related_concept,
        summary=summary,
        event_year=event_year,
        citation=citation,
    )


def persist_outline(
    outline: Dict[str, Any] | List[Dict[str, Any]],
    *,
    version: int | None = None,
    source_uri: str | None = None,
    metadata: Dict[str, Any] | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    return _adapter(store_path).persist_outline(
        outline,
        version=version,
        source_uri=source_uri,
        metadata=metadata,
    )
