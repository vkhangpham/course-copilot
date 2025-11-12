"""Adapter objects that encapsulate access to the world-model store."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

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
