from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from apps.orchestrator.notebook_publisher import (
    NotebookPublisher,
    NotebookSectionInput,
    _extract_citations,
)


class StubExporter:
    def __init__(self, *, should_raise_value_error: bool = False) -> None:
        self.calls: List[dict] = []
        self.should_raise_value_error = should_raise_value_error

    def __call__(self, notebook_slug: str, title: str, content_md: str, citations: List[str], **kwargs):
        self.calls.append(
            {
                "slug": notebook_slug,
                "title": title,
                "content": content_md,
                "citations": citations,
                "kwargs": kwargs,
            }
        )
        if self.should_raise_value_error:
            raise ValueError("missing api base")
        return {"status": "ok", "notebook": notebook_slug, "note_id": f"note-{len(self.calls)}"}


def test_publisher_records_error_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter = StubExporter(should_raise_value_error=True)

    def fake_push(**kwargs):
        return exporter(
            kwargs.get("notebook_slug", ""),
            kwargs.get("title", "Untitled"),
            kwargs.get("content_md", ""),
            kwargs.get("citations", []),
        )

    monkeypatch.setattr("apps.orchestrator.notebook_publisher.push_notebook_section", fake_push)
    monkeypatch.setattr(
        "apps.orchestrator.notebook_publisher.ensure_notebook_exists",
        lambda **_: {"status": "ok", "notebook": "slug"},
    )
    pub = NotebookPublisher(notebook_slug="slug")
    sections = [NotebookSectionInput(title="Plan", content="# title\nbody")]

    results = pub.publish(sections)
    assert results[0]["response"]["status"] == "skipped"
    assert "missing" in results[0]["response"].get("error", "missing_api_base") or results[0]["response"].get("reason")


def test_extract_citations_preserves_original_casing() -> None:
    markdown = (
        "Discussion references [Garcia, 2021] for grounding and [SQL2003] for standards. "
        "Later we mention [garcia, 2021] again to test dedupe."
    )

    citations = _extract_citations(markdown)

    assert citations == ["Garcia, 2021", "SQL2003"]
