"""Lightweight JSONL provenance logger for the CourseGen PoC pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from pydantic import BaseModel, Field


class ProvenanceEvent(BaseModel):
    """Structured record for pipeline activity."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stage: str = Field(..., description="High-level pipeline stage, e.g. 'ingest' or 'student_eval'.")
    message: str = Field(..., description="Human-readable description of the event.")
    agent: str = Field(default="system")
    payload: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceLogger:
    """Append-only JSONL logger for provenance and debugging."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: ProvenanceEvent | Dict[str, Any]) -> ProvenanceEvent:
        """Write a single event to disk and return the normalized object."""
        if not isinstance(event, ProvenanceEvent):
            event = ProvenanceEvent(**event)
        line = event.model_dump_json()
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return event

    def extend(self, events: Iterable[ProvenanceEvent | Dict[str, Any]]) -> None:
        """Batch-write multiple events."""
        for event in events:
            self.log(event)


__all__ = ["ProvenanceEvent", "ProvenanceLogger"]
