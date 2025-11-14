"""TA role for synthesizing database systems history/timeline."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from ccopilot.utils.split_fields import split_fields


@dataclass
class TimelineEvent:
    year: int | None
    event: str
    impact: str
    concepts: List[str]


class TimelineSynthesizer:
    """Surface curated timeline events for TA prompts."""

    def build(
        self,
        timeline_file: Path,
        *,
        concepts: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> List[TimelineEvent]:
        rows = self._load_rows(timeline_file)
        filter_set = {concept.lower() for concept in concepts} if concepts else set()

        events: List[TimelineEvent] = []
        for row in rows:
            event_label = row.get("event") or row.get("event_label")
            if not event_label:
                continue
            related = self._split_concepts(row.get("related_concepts"))
            if filter_set and not filter_set.intersection(concept.lower() for concept in related):
                continue
            event = TimelineEvent(
                year=self._parse_year(row.get("year")),
                event=event_label,
                impact=row.get("why_it_matters") or row.get("summary") or row.get("impact") or "",
                concepts=related,
            )
            events.append(event)

        events.sort(key=lambda item: (item.year is None, item.year or 0))
        if limit is not None and limit >= 0:
            events = events[:limit]
        return events

    # ------------------------------------------------------------------

    @staticmethod
    def _load_rows(timeline_file: Path) -> List[dict]:
        path = timeline_file.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [row for row in reader]

    @staticmethod
    def _split_concepts(raw: str | None) -> List[str]:
        return split_fields(raw)

    @staticmethod
    def _parse_year(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
