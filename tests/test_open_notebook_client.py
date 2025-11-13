import json

import httpx
import pytest

from apps.codeact.tools.open_notebook import (
    _reset_auto_create_cache_for_testing,
    push_notebook_section,
)
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


def test_open_notebook_client_ensure_notebook_creates_when_missing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(201, json={"id": "notebook-123"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook.test")
    client = OpenNotebookClient(
        OpenNotebookConfig(base_url="https://notebook.test", api_key="secret-token"),
        client=http_client,
    )

    result = client.ensure_notebook("database-systems-poc", description="CourseGen PoC")

    assert result["id"] == "notebook-123"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/notebooks")
    assert captured["authorization"] == "Bearer secret-token"
    assert captured["payload"] == {"name": "database-systems-poc", "description": "CourseGen PoC"}


def test_open_notebook_client_ensure_notebook_handles_conflict() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"status": "exists"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook.test")
    client = OpenNotebookClient(OpenNotebookConfig(base_url="https://notebook.test"), client=http_client)

    result = client.ensure_notebook("database-systems-poc")

    assert result == {"status": "exists", "notebook": "database-systems-poc"}


def test_open_notebook_client_ensure_notebook_handles_empty_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook.test")
    client = OpenNotebookClient(OpenNotebookConfig(base_url="https://notebook.test"), client=http_client)

    result = client.ensure_notebook("nb")

    assert result == {"status": "ok", "notebook": "nb"}


def test_push_notebook_section_uses_env_defaults(monkeypatch) -> None:
    monkeypatch.setenv("OPEN_NOTEBOOK_API_BASE", "https://env-base")
    monkeypatch.setenv("OPEN_NOTEBOOK_API_KEY", "env-token")
    monkeypatch.setenv("OPEN_NOTEBOOK_AUTO_CREATE", "0")

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


def test_push_notebook_section_reuses_auto_create_cache(monkeypatch) -> None:
    _reset_auto_create_cache_for_testing()
    monkeypatch.setenv("OPEN_NOTEBOOK_API_BASE", "https://cache-base")
    monkeypatch.setenv("OPEN_NOTEBOOK_API_KEY", "cache-token")

    calls = {"ensure": 0, "push": 0}

    class FakeClient:
        def ensure_notebook(self, *args, **kwargs):
            calls["ensure"] += 1
            return {"status": "ok", "notebook": args[0]}

        def push_note(self, *args, **kwargs):
            calls["push"] += 1
            return {"status": "ok"}

        def close(self) -> None:
            pass

    client = FakeClient()

    push_notebook_section(notebook_slug="slug-a", title="One", content_md="Body", client=client)
    push_notebook_section(notebook_slug="slug-a", title="Two", content_md="Body", client=client)

    assert calls["ensure"] == 1, "ensure_notebook should only run once per base/slug"
    assert calls["push"] == 2
@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    _reset_auto_create_cache_for_testing()
