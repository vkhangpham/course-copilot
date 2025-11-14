import json

import httpx
import pytest

from apps.codeact.tools.open_notebook import (
    _reset_auto_create_cache_for_testing,
    ensure_notebook_exists,
)
from apps.codeact.tools_open_notebook import OpenNotebookClient, OpenNotebookConfig


@pytest.fixture()
def notebook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPEN_NOTEBOOK_SLUG", "preflight-slug")
    monkeypatch.setenv("OPEN_NOTEBOOK_API_BASE", "https://notebook-preflight.test")
    monkeypatch.setenv("OPEN_NOTEBOOK_API_KEY", "fake-token")


def test_ensure_notebook_exists_calls_create(monkeypatch: pytest.MonkeyPatch, notebook_env) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"status": "created"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://notebook-preflight.test")
    client = OpenNotebookClient(OpenNotebookConfig(base_url="https://notebook-preflight.test", api_key="fake-token"), client=http_client)

    result = ensure_notebook_exists(client=client)

    assert result["status"] == "created"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/notebooks")
    assert captured["payload"] == {"name": "preflight-slug"}
    assert captured["authorization"] == "Bearer fake-token"


def test_ensure_notebook_exists_requires_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPEN_NOTEBOOK_API_BASE", raising=False)
    monkeypatch.setenv("OPEN_NOTEBOOK_SLUG", "missing-base")
    with pytest.raises(ValueError):
        ensure_notebook_exists()


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    _reset_auto_create_cache_for_testing()
