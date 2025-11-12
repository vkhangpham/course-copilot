import json

import httpx
import pytest

from apps.codeact.tools.open_notebook import push_notebook_section
from apps.codeact.tools_open_notebook import OpenNotebookClient, OpenNotebookConfig


def test_open_notebook_client_push_note_posts_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(201, json={"id": "section-123"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook.test")
    client = OpenNotebookClient(
        OpenNotebookConfig(base_url="https://notebook.test", api_key="secret-token"),
        client=http_client,
    )

    result = client.push_note(
        "database-systems-poc",
        "Week 1",
        "## Lesson",
        ["codd-1970"],
    )

    assert result == {"id": "section-123"}
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/notebooks/database-systems-poc/sections")
    assert captured["authorization"] == "Bearer secret-token"
    assert captured["payload"] == {
        "title": "Week 1",
        "content": "## Lesson",
        "citations": ["codd-1970"],
    }

def test_open_notebook_client_raises_for_http_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook.test")
    client = OpenNotebookClient(
        OpenNotebookConfig(base_url="https://notebook.test"),
        client=http_client,
    )

    with pytest.raises(httpx.HTTPStatusError):
        client.push_note("nb", "Title", "Body", [])


def test_push_notebook_section_uses_env_defaults(monkeypatch) -> None:
    monkeypatch.setenv("OPEN_NOTEBOOK_API_BASE", "https://env-base")
    monkeypatch.setenv("OPEN_NOTEBOOK_API_KEY", "env-token")

    calls: dict[str, object] = {}

    class FakeClient:
        def __init__(self, config: OpenNotebookConfig):
            calls["config"] = config

        def push_note(self, *args):
            calls["args"] = args
            return {"status": "ok"}

        def close(self) -> None:
            calls["closed"] = True

    monkeypatch.setattr(
        "apps.codeact.tools.open_notebook.OpenNotebookClient",
        lambda config: FakeClient(config),
    )

    response = push_notebook_section(
        notebook_slug="notebook-a",
        title="Section",
        content_md="Body",
        citations=["cite-1"],
    )

    assert response == {"status": "ok"}
    config = calls["config"]
    assert isinstance(config, OpenNotebookConfig)
    assert config.base_url == "https://env-base"
    assert config.api_key == "env-token"
    assert calls["args"][0] == "notebook-a"
    assert calls.get("closed") is True


def test_push_notebook_section_requires_api_base(monkeypatch) -> None:
    monkeypatch.delenv("OPEN_NOTEBOOK_API_BASE", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_API_KEY", raising=False)

    with pytest.raises(ValueError):
        push_notebook_section(
            notebook_slug="nb",
            title="Sec",
            content_md="Body",
        )
