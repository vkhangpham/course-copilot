from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from apps.orchestrator import notebook_publisher as publisher_mod
from apps.orchestrator.notebook_publisher import (
    NotebookPublisher,
    NotebookSectionInput,
    build_sections_from_markdown,
    chunk_markdown_sections,
)


def test_extract_citations_normalizes_tokens() -> None:
    text = """
    ## Sample Section
    Discussed ARIES [aries-1992] alongside System R [system-r-1976].
    Refer to `[codd-1970]` again and `[ARIES-1992]` for emphasis.
    """

    citations = publisher_mod._extract_citations(text)
    assert citations == ["aries-1992", "codd-1970", "system-r-1976"]


def test_derive_title_prefers_first_heading() -> None:
    markdown = """
    Intro text
    # Week 1 — Relational Thinking
    Content goes here
    """

    derived = NotebookPublisher._derive_title(markdown, fallback="Fallback Title")
    assert derived == "Week 1 — Relational Thinking"


def test_derive_title_handles_bom_heading() -> None:
    markdown = "\ufeff# Week 1 – Overview\nContent goes here"
    derived = NotebookPublisher._derive_title(markdown, fallback="Fallback Title")
    assert derived == "Week 1 – Overview"


def test_publish_invokes_push_notebook_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[dict] = []

    def fake_push(**kwargs):
        calls.append(kwargs)
        return {"status": "ok", "title": kwargs["title"]}

    monkeypatch.setattr(publisher_mod, "push_notebook_section", fake_push)

    plan_path = tmp_path / "plan.md"
    plan_path.write_text("# Week 1\nPlan content [codd-1970]", encoding="utf-8")
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("## Lecture\nNotes [system-r-1976]", encoding="utf-8")

    pub = NotebookPublisher(
        notebook_slug="db-course",
        api_base="http://mock",
        api_key="token",
    )
    results = pub.publish(
        [
            NotebookSectionInput(title="Course Plan", path=plan_path),
            NotebookSectionInput(title="Lecture", path=lecture_path),
        ]
    )

    assert len(results) == 3
    assert results[0]["kind"] == "preflight"
    assert calls[0]["notebook_slug"] == "db-course"
    assert calls[0]["citations"] == ["codd-1970"]
    assert calls[1]["citations"] == ["system-r-1976"]
    assert results[1]["response"]["status"] == "ok"


def test_publish_skips_missing_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.md"
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("# Exists\nBody", encoding="utf-8")

    calls: List[dict] = []

    def fake_push(**kwargs):
        calls.append(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(publisher_mod, "push_notebook_section", fake_push)

    pub = NotebookPublisher(notebook_slug="db-course")
    results = pub.publish(
        [
            NotebookSectionInput(title="Missing", path=missing),
            NotebookSectionInput(title="Lecture", path=lecture_path),
        ]
    )

    assert len(results) == 2  # preflight + single section
    assert results[0]["kind"] == "preflight"
    assert calls[0]["title"] == "Exists"


def test_publish_returns_placeholder_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lecture_path = tmp_path / "lecture.md"
    lecture_path.write_text("# Lecture\nBody", encoding="utf-8")

    def failing_push(**kwargs):
        raise ValueError("offline export")

    monkeypatch.setattr(publisher_mod, "push_notebook_section", failing_push)

    pub = NotebookPublisher(notebook_slug="db-course")
    results = pub.publish([NotebookSectionInput(title="Lecture", path=lecture_path)])

    assert results[0]["kind"] == "preflight"
    assert results[1]["response"]["status"] == "skipped"


def test_publish_supports_inline_content(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[dict] = []

    def fake_push(**kwargs):
        calls.append(kwargs)
        return {"status": "ok", "note_id": "chunk-1"}

    monkeypatch.setattr(publisher_mod, "push_notebook_section", fake_push)

    section = NotebookSectionInput(title="Chunk A", content="# Heading\nBody text")
    pub = NotebookPublisher(notebook_slug="db-course")
    results = pub.publish([section])

    assert results[0]["kind"] == "preflight"
    assert results[1]["title"] == "Chunk A"
    assert calls[0]["title"] == "Chunk A"
    assert calls[0]["content_md"].startswith("# Heading")


def test_publish_preflight_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        publisher_mod,
        "push_notebook_section",
        lambda **kwargs: {"status": "ok"},
    )
    pub = NotebookPublisher(notebook_slug="db-course", auto_create=False)
    results = pub.publish([NotebookSectionInput(title="Section", content="# One\nBody")])
    assert results[0]["response"]["reason"] == "auto_create_disabled"


def test_publish_preflight_handles_missing_api_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        publisher_mod,
        "push_notebook_section",
        lambda **kwargs: {"status": "ok"},
    )
    pub = NotebookPublisher(notebook_slug="db-course", api_base=None, auto_create=True)
    results = pub.publish([NotebookSectionInput(title="Section", content="# One\nBody")])
    assert results[0]["response"]["status"] == "skipped"
    assert results[0]["response"]["reason"] == "missing_api_base"


def test_chunk_markdown_sections_extracts_headings() -> None:
    markdown = """# Intro\nline\n## Week 1\ncontent\n## Week 2\nmore"""
    chunks = chunk_markdown_sections(markdown, "Fallback")
    assert len(chunks) == 3
    titles = [title for title, _ in chunks]
    assert titles == ["Intro", "Week 1", "Week 2"]
    # Ensure heading text is not duplicated inside the section body.
    assert chunks[0][1] == "line"
    assert chunks[1][1] == "content"
    assert chunks[2][1] == "more"


def test_chunk_markdown_sections_handles_bom_prefixed_headings() -> None:
    markdown = "\ufeff# Intro\nline\n## Week 1\ncontent"
    chunks = chunk_markdown_sections(markdown, "Fallback")
    assert chunks[0][0] == "Intro"
    assert chunks[0][1] == "line"
    assert chunks[1][0] == "Week 1"
    assert chunks[1][1] == "content"


def test_build_sections_from_markdown_limits_sections(tmp_path: Path) -> None:
    doc = tmp_path / "plan.md"
    doc.write_text("# Intro\nalpha\n## Week 1\nbody\n## Week 2\nbody\n", encoding="utf-8")
    sections = build_sections_from_markdown(doc, "Course Plan", max_sections=2)
    assert len(sections) == 2
    assert sections[0].title == "Intro"
    assert sections[1].title == "Week 1"
    assert sections[0].content is not None
