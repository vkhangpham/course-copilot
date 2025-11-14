"""Stateful helpers that surface the symbolic world model to CodeAct."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from apps.codeact.tools import world_model as world_model_tools
from apps.codeact.tools.data import load_dataset_asset


class WorldModelTools:
    """Expose read-heavy world-model helpers with dataset fallbacks.

    The orchestrator hands a dataset root (``concept_root``) to every TA.  The
    ``WorldModelTools`` facade first attempts to resolve requests against the
    live SQLite store backing the symbolic world model; if the store is not yet
    available (for example on a fresh checkout before ingestion runs), it falls
    back to the handcrafted YAML concepts bundle.
    """

    def __init__(self, concept_root: Path, *, store_path: Path | str | None = None) -> None:
        self.concept_root = Path(concept_root).expanduser().resolve()
        self._store_path = Path(store_path).expanduser().resolve() if store_path else None
        self._dataset_cache: dict[str, dict[str, Any]] | None = None
        self._children_index: dict[str, list[str]] | None = None

    def query(self, concept_id: str) -> Dict[str, Any]:
        """Return the best-match concept payload from the world model.

        The lookup prioritizes the SQLite world model store so CodeAct sessions
        observe the same state mutations that other agents create.  When the
        store has not been ingested yet, the method falls back to the
        handcrafted dataset to keep local development productive.
        """

        normalized = self._normalize_identifier(concept_id)
        if not normalized:
            raise ValueError("concept_id must be a non-empty string")

        records = self._fetch_from_store(topic=normalized)
        from_store = self._select_match(records, normalized)
        if from_store is not None:
            return self._merge_dataset_metadata(from_store)

        fallback = self._lookup_dataset_concept(normalized)
        if fallback is not None:
            return fallback

        raise KeyError(f"Concept not found: {concept_id}")

    def list_concepts(self) -> List[Dict[str, Any]]:
        """Enumerate concepts, preferring the authoritative store when present."""

        records = self._fetch_from_store()
        if records:
            return [self._merge_dataset_metadata(record) for record in records]

        dataset_map = self._load_dataset_concepts()
        return [dataset_map[key] for key in sorted(dataset_map.keys())]

    # ------------------------------------------------------------------
    # Internal helpers

    def _fetch_from_store(self, topic: str | None = None) -> List[Dict[str, Any]]:
        try:
            return world_model_tools.fetch_concepts(
                topic=topic,
                depth=4,
                limit=None,
                store_path=self._store_path,
            )
        except FileNotFoundError:
            return []

    def _select_match(self, records: List[Dict[str, Any]], identifier: str) -> Dict[str, Any] | None:
        if not records:
            return None
        lowered = identifier.lower()
        for record in records:
            if record.get("id", "").lower() == lowered:
                return record
        for record in records:
            if record.get("name", "").lower() == lowered:
                return record
        return None

    def _lookup_dataset_concept(self, identifier: str) -> Dict[str, Any] | None:
        dataset_map = self._load_dataset_concepts()
        if identifier in dataset_map:
            return dataset_map[identifier]
        lowered = identifier.lower()
        for payload in dataset_map.values():
            if payload.get("name", "").lower() == lowered:
                return payload
        return None

    def _load_dataset_concepts(self) -> dict[str, dict[str, Any]]:
        if self._dataset_cache is not None:
            return self._dataset_cache

        asset = load_dataset_asset("concepts.yaml", base_dir=self.concept_root)
        concepts = asset.get("concepts") if isinstance(asset, dict) else {}
        dataset: dict[str, dict[str, Any]] = {}
        children: dict[str, list[str]] = {}
        if isinstance(concepts, dict):
            for concept_id, payload in concepts.items():
                dataset[concept_id] = self._normalize_dataset_payload(concept_id, payload)
                parent = payload.get("parent")
                if parent:
                    children.setdefault(parent, []).append(concept_id)
        for parent, child_ids in children.items():
            if parent in dataset:
                dataset[parent]["children"] = sorted(child_ids)
        self._dataset_cache = dataset
        self._children_index = {key: list(value) for key, value in children.items()}
        return dataset

    @staticmethod
    def _normalize_identifier(identifier: str | None) -> str:
        if not identifier:
            return ""
        return identifier.strip()

    @staticmethod
    def _normalize_dataset_payload(concept_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        name = payload.get("name") or concept_id.replace("_", " ").title()
        return {
            "id": concept_id,
            "name": name,
            "summary": payload.get("summary", ""),
            "parent_id": payload.get("parent"),
            "prerequisites": list(payload.get("prerequisites") or []),
            "canonical_sources": list(payload.get("canonical_sources") or []),
            "children": [],
        }

    def _merge_dataset_metadata(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        dataset_map = self._load_dataset_concepts()
        meta = dataset_map.get(entry.get("id"))
        if not meta:
            return entry
        merged = dict(entry)
        if not merged.get("canonical_sources") and meta.get("canonical_sources"):
            merged["canonical_sources"] = meta["canonical_sources"]
        if not merged.get("prerequisites") and meta.get("prerequisites"):
            merged["prerequisites"] = meta["prerequisites"]
        if not merged.get("summary") and meta.get("summary"):
            merged["summary"] = meta["summary"]
        if merged.get("parent_id") is None and meta.get("parent_id") is not None:
            merged["parent_id"] = meta["parent_id"]
        if not merged.get("children") and meta.get("children"):
            merged["children"] = meta["children"]
        return merged
