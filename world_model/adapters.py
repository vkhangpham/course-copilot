"""Adapter objects that encapsulate access to the world-model store."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from .storage import WorldModelStore


@dataclass
class WorldModelAdapter:
    store_path: Path

    def __post_init__(self) -> None:
        self.store = WorldModelStore(self.store_path)

    # ------------------------------------------------------------------
    # Concept graph helpers

    def fetch_concepts(self, topic: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, name, summary, parent_id FROM concepts"
        params: tuple[Any, ...] = tuple()
        if topic:
            sql += " WHERE name LIKE ? OR id LIKE ?"
            like = f"%{topic}%"
            params = (like, like)
        rows = self.store.query(sql, params)
        return [
            {"id": row[0], "name": row[1], "summary": row[2], "parent_id": row[3]}
            for row in rows
        ]

    def fetch_concept_tree(
        self,
        *,
        topic: str | None = None,
        max_depth: int = 1,
        limit: int | None = 50,
    ) -> list[dict[str, Any]]:
        """Return a breadth-first slice of the concept hierarchy."""

        concept_rows = self.store.query("SELECT id, name, summary, parent_id FROM concepts")
        if not concept_rows:
            return []

        nodes = {
            row[0]: {
                "id": row[0],
                "name": row[1],
                "summary": row[2],
                "parent_id": row[3],
            }
            for row in concept_rows
        }

        relation_rows = self.store.query(
            "SELECT source_id, target_id, relation_type FROM relationships"
        )
        children_map: Dict[str | None, List[str]] = defaultdict(list)
        prereq_map: Dict[str, List[str]] = defaultdict(list)
        for source_id, target_id, relation_type in relation_rows:
            if relation_type == "is_part_of":
                children_map[target_id].append(source_id)
            elif relation_type == "prerequisite":
                prereq_map[target_id].append(source_id)

        if topic:
            lowered = topic.lower()
            start_ids = [
                concept_id
                for concept_id, payload in nodes.items()
                if lowered in payload["name"].lower() or lowered in concept_id.lower()
            ]
        else:
            start_ids = [concept_id for concept_id, payload in nodes.items() if not payload["parent_id"]]

        if not start_ids:
            start_ids = list(nodes.keys())

        queue = deque([(concept_id, 0) for concept_id in start_ids])
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        max_depth = max(0, max_depth)

        while queue:
            concept_id, depth = queue.popleft()
            if concept_id in seen:
                continue
            node = nodes.get(concept_id)
            if not node:
                continue
            seen.add(concept_id)
            entry = {
                **node,
                "depth": depth,
                "children": children_map.get(concept_id, []),
                "prerequisites": prereq_map.get(concept_id, []),
            }
            results.append(entry)
            if limit is not None and len(results) >= limit:
                break
            if depth < max_depth:
                for child_id in children_map.get(concept_id, []):
                    queue.append((child_id, depth + 1))

        return results

    # ------------------------------------------------------------------
    # Timeline / literature helpers

    def search_timeline(
        self,
        *,
        query: str | None = None,
        concept_id: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT event_year, event_label, summary, related_concept, citation "
            "FROM observations WHERE 1=1"
        )
        params: list[Any] = []
        if concept_id:
            sql += " AND related_concept = ?"
            params.append(concept_id)
        if query:
            sql += " AND (event_label LIKE ? OR summary LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like])
        sql += " ORDER BY event_year IS NULL, event_year ASC LIMIT ?"
        params.append(limit)
        rows = self.store.query(sql, tuple(params))
        return [
            {
                "year": row[0],
                "event": row[1],
                "summary": row[2],
                "concept_id": row[3],
                "citation_id": row[4],
            }
            for row in rows
        ]

    def lookup_paper(self, paper_id: str) -> dict[str, Any] | None:
        rows = self.store.query(
            "SELECT id, title, venue, year, url FROM papers WHERE id = ?",
            (paper_id,),
        )
        if not rows:
            return None
        row = rows[0]
        author_rows = self.store.query(
            """
            SELECT a.id, a.full_name, a.affiliation
            FROM paper_authors pa
            JOIN authors a ON a.id = pa.author_id
            WHERE pa.paper_id = ?
            ORDER BY pa.position ASC
            """,
            (paper_id,),
        )
        return {
            "id": row[0],
            "title": row[1],
            "venue": row[2],
            "year": row[3],
            "url": row[4],
            "authors": [
                {"id": author_id, "name": name, "affiliation": affiliation}
                for author_id, name, affiliation in author_rows
            ],
        }

    # ------------------------------------------------------------------
    # Mutation helpers

    def record_claim(
        self,
        *,
        subject: str,
        content: str,
        citation: str | None = None,
        created_by: str = "tool",
    ) -> dict[str, Any]:
        sql = "INSERT INTO claims(subject_id, body, citation, created_by) VALUES (?, ?, ?, ?)"
        claim_id = self.store.execute(sql, (subject, content, citation, created_by))
        return {
            "id": claim_id,
            "subject": subject,
            "body": content,
            "citation": citation,
        }

    def list_claims(
        self,
        *,
        subject_id: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        sql = "SELECT id, subject_id, body, citation, created_at FROM claims WHERE 1=1"
        params: List[Any] = []
        if subject_id:
            sql += " AND subject_id = ?"
            params.append(subject_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.store.query(sql, tuple(params))
        return [
            {
                "id": row[0],
                "subject_id": row[1],
                "body": row[2],
                "citation": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def list_relationships(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        relation_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT source_id, target_id, relation_type, justification "
            "FROM relationships WHERE 1=1"
        )
        params: List[Any] = []
        if source_id:
            sql += " AND source_id = ?"
            params.append(source_id)
        if target_id:
            sql += " AND target_id = ?"
            params.append(target_id)
        if relation_type:
            sql += " AND relation_type = ?"
            params.append(relation_type)
        sql += " ORDER BY id ASC LIMIT ?"
        params.append(limit)
        rows = self.store.query(sql, tuple(params))
        return [
            {
                "source_id": row[0],
                "target_id": row[1],
                "relation_type": row[2],
                "justification": row[3],
            }
            for row in rows
        ]

    def link_concepts(
        self,
        *,
        source_id: str,
        target_id: str,
        relation_type: str,
        justification: str | None = None,
    ) -> dict[str, Any]:
        """Create or reinforce a relationship between two concepts."""

        self._ensure_concepts_exist([source_id, target_id])
        relation = relation_type.strip() if relation_type else "related_to"
        note = (justification or "Added via CodeAct").strip()
        rel_id = self.store.execute(
            "INSERT INTO relationships (source_id, target_id, relation_type, justification) "
            "VALUES (?, ?, ?, ?)",
            (source_id, target_id, relation, note),
        )
        return {
            "id": rel_id,
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation,
            "justification": note,
        }

    def append_timeline_event(
        self,
        *,
        event_label: str,
        related_concept: str,
        summary: str | None = None,
        event_year: int | None = None,
        citation: str | None = None,
    ) -> dict[str, Any]:
        """Append a timeline event linked to a concept."""

        if not event_label:
            raise ValueError("event_label is required")
        self._ensure_concepts_exist([related_concept])
        event_id = self.store.execute(
            "INSERT INTO observations (event_year, event_label, summary, related_concept, citation) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_year, event_label, summary, related_concept, citation),
        )
        return {
            "id": event_id,
            "year": event_year,
            "event": event_label,
            "summary": summary,
            "concept_id": related_concept,
            "citation": citation,
        }

    def persist_outline(
        self,
        outline: Dict[str, Any] | List[Dict[str, Any]],
        *,
        version: int | None = None,
        source_uri: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store an outline artifact so downstream agents can reuse it."""

        artifact_uri = source_uri or f"codeact://course_outline/{uuid4().hex}"
        payload = {
            "version": version,
            "outline": outline,
        }
        if metadata:
            payload["metadata"] = metadata
        artifact_id = self.store.execute(
            "INSERT INTO artifacts (artifact_type, uri, metadata) VALUES (?, ?, ?)",
            ("course_outline", artifact_uri, json.dumps(payload, ensure_ascii=False)),
        )
        return {"id": artifact_id, "uri": artifact_uri, "payload": payload}

    # ------------------------------------------------------------------
    # Internal helpers

    def _ensure_concepts_exist(self, concept_ids: Iterable[str]) -> None:
        ids = [concept_id for concept_id in concept_ids if concept_id]
        if not ids:
            raise ValueError("At least one concept id is required")
        placeholders = ",".join("?" for _ in ids)
        rows = self.store.query(
            f"SELECT id FROM concepts WHERE id IN ({placeholders})",
            tuple(ids),
        )
        found = {row[0] for row in rows}
        missing = sorted(set(ids) - found)
        if missing:
            raise ValueError(f"Unknown concept id(s): {', '.join(missing)}")
