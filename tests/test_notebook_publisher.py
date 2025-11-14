from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from apps.codeact.tools.open_notebook import _reset_auto_create_cache_for_testing
from apps.orchestrator.notebook_publisher import (
    NotebookPublisher,
    NotebookSectionInput,
    _extract_citations,
    build_sections_from_markdown,
)
from ccopilot.core.validation import ValidationFailure


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


def test_resolve_markdown_raises_for_missing_file(tmp_path: Path) -> None:
    publisher = NotebookPublisher(notebook_slug="slug", auto_create=False)
    section = NotebookSectionInput(title="Missing", path=tmp_path / "missing.md")

    with pytest.raises(FileNotFoundError):
        publisher._resolve_markdown(section)


def test_build_sections_from_markdown_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationFailure):
        build_sections_from_markdown(tmp_path / "missing.md", "Fallback")


def test_build_sections_from_markdown_rejects_directories(tmp_path: Path) -> None:
    directory = tmp_path / "dir"
    directory.mkdir()

    with pytest.raises(ValidationFailure):
        build_sections_from_markdown(directory, "Dir")


def test_publish_records_missing_markdown(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    publisher = NotebookPublisher(notebook_slug="slug")
    section = NotebookSectionInput(title="Missing", path=tmp_path / "missing.md")

    with caplog.at_level("ERROR"):
        results = publisher.publish([section])

    assert results
    last_entry = results[-1]
    assert last_entry["response"]["status"] == "skipped"
    assert last_entry["response"]["reason"] == "missing_markdown"


def test_publish_handles_non_file_sections(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    publisher = NotebookPublisher(notebook_slug="slug")
    directory_path = tmp_path / "dir_section"
    directory_path.mkdir()
    section = NotebookSectionInput(title="Dir", path=directory_path)

    with caplog.at_level("ERROR"):
        results = publisher.publish([section])

    assert any("failed validation" in record.message for record in caplog.records)
    last_entry = results[-1]
    assert last_entry["response"]["status"] == "error"


def test_preflight_marks_notebook_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_auto_create_cache_for_testing()
    import apps.codeact.tools.open_notebook as open_nb

    orig_ensure = open_nb.ensure_notebook_exists
    ensure_calls: list[tuple[str | None, str | None]] = []

    def tracking_ensure(**kwargs):
        ensure_calls.append((kwargs.get("api_base"), kwargs.get("notebook_slug")))
        return orig_ensure(**kwargs)

    monkeypatch.setattr(open_nb, "ensure_notebook_exists", tracking_ensure)
    monkeypatch.setattr("apps.orchestrator.notebook_publisher.ensure_notebook_exists", tracking_ensure)

    class FakeClient:
        def __init__(self, config, *, client=None, timeout: float = 30.0) -> None:  # noqa: D401 - test stub
            self._config = config
            self._owns_client = True

        def push_note(self, notebook_id: str, title: str, content_md: str, citations: list[str]) -> dict:
            return {"status": "ok", "notebook": notebook_id, "note_id": f"{notebook_id}-0001"}

        def ensure_notebook(self, notebook_id: str, *, description: str | None = None) -> dict:
            return {"status": "created", "notebook": notebook_id, "description": description}

        def close(self) -> None:  # pragma: no cover - no-op for test stub
            pass

    monkeypatch.setattr(open_nb, "OpenNotebookClient", FakeClient)

    publisher = NotebookPublisher(
        notebook_slug="test-notebook",
        api_base="https://api.notebook.local",
        api_key="token",
        auto_create=True,
    )
    sections = [NotebookSectionInput(title="Plan", content="# Week 1\nBody")]

    publisher.publish(sections)

    assert ensure_calls == [("https://api.notebook.local", "test-notebook")]
