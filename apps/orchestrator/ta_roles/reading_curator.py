"""TA role for curating readings and citations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class ReadingRecommendation:
    identifier: str
    title: str
    why_it_matters: str
    citation: str


class ReadingCurator:
    """Surface high-signal readings from the handcrafted dataset."""

    def curate(
        self,
        concept_root: Path,
        *,
        keywords: Sequence[str] | None = None,
        limit: int | None = 5,
    ) -> List[ReadingRecommendation]:
        papers = self._load_papers(concept_root)
        keyword_set = {kw.strip().lower() for kw in (keywords or []) if kw.strip()}

        recommendations: List[ReadingRecommendation] = []
        for paper in papers:
            if keyword_set and not self._match_keywords(paper, keyword_set):
                continue
            recommendations.append(self._recommendation_from_row(paper))

        recommendations.sort(key=lambda rec: rec.identifier)
        if limit is not None and limit >= 0:
            recommendations = recommendations[:limit]
        return recommendations

    # ------------------------------------------------------------------

    @staticmethod
    def _load_papers(dataset_root: Path) -> List[dict]:
        path = (dataset_root / "papers.csv").expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader]

    @staticmethod
    def _match_keywords(row: dict, keyword_set: set[str]) -> bool:
        haystacks = [
            row.get("id", ""),
            row.get("title", ""),
            row.get("key_points", ""),
        ]
        combined = " ".join(haystacks).lower()
        return any(keyword in combined for keyword in keyword_set)

    @staticmethod
    def _recommendation_from_row(row: dict) -> ReadingRecommendation:
        identifier = row.get("id", "unknown")
        title = row.get("title", "Untitled")
        key_points = row.get("key_points") or row.get("summary") or "Review foundational ideas."
        authors = (row.get("authors") or "").replace(";", ", ")
        year = row.get("year") or "n.d."
        venue = row.get("venue") or ""
        citation = ", ".join(filter(None, [authors, f"({year})", title, venue]))
        return ReadingRecommendation(
            identifier=identifier,
            title=title,
            why_it_matters=key_points,
            citation=citation,
        )
