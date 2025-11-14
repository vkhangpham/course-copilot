from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest

from apps.codeact.tools.open_notebook import (
    _reset_auto_create_cache_for_testing,
    push_notebook_section,
)


class _MinimalNotebookClient:
    """Client stub that only implements push_note (no ensure_notebook)."""

    def __init__(self) -> None:
        self.push_calls: List[Dict[str, Any]] = []

    def push_note(
        self,
        notebook_id: str,
        title: str,
        content_md: str,
        citations: List[str],
        notebook_record_id: str | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "notebook": notebook_id,
            "title": title,
            "content": content_md,
            "citations": citations,
            "record": notebook_record_id,
        }
        self.push_calls.append(payload)
        return {"status": "ok", "notebook": notebook_id}


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    _reset_auto_create_cache_for_testing()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OPEN_NOTEBOOK_SLUG", "OPEN_NOTEBOOK_API_BASE", "OPEN_NOTEBOOK_API_KEY", "OPEN_NOTEBOOK_AUTO_CREATE"):
        monkeypatch.delenv(key, raising=False)


def test_push_notebook_section_handles_client_without_ensure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[Dict[str, Any]] = []

    def fake_ensure(**kwargs):
        calls.append(kwargs)
        return {"status": "skipped", "reason": "client_missing_ensure"}

    monkeypatch.setattr("apps.codeact.tools.open_notebook.ensure_notebook_exists", fake_ensure)
    os.environ["OPEN_NOTEBOOK_SLUG"] = "client-missing-ensure"
    os.environ["OPEN_NOTEBOOK_API_BASE"] = "http://api-three"
    os.environ["OPEN_NOTEBOOK_API_KEY"] = "token"

    client = _MinimalNotebookClient()
    first = push_notebook_section(title="Section 1", content_md="Body", client=client)
    assert first["status"] == "ok"
    assert client.push_calls, "expected push_note to run"
    assert calls and calls[0]["client"] is None

    second = push_notebook_section(title="Section 2", content_md="Body", client=client)
    assert second["status"] == "ok"
    assert len(client.push_calls) == 2
    assert len(calls) == 1, "cache should prevent repeated ensure calls for same slug/base"
