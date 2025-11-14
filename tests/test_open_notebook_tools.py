import json
import os
from pathlib import Path

import httpx
import pytest

from apps.codeact.tools.open_notebook import (
    EXPORT_DIR_ENV,
    EXPORT_MIRROR_ENV,
    _reset_auto_create_cache_for_testing,
    push_notebook_section,
)
from apps.codeact.tools_open_notebook import OpenNotebookClient, OpenNotebookConfig
from tests.mocks.notebook_api import NotebookAPIMock


@pytest.fixture()
def notebook_api_client() -> tuple[NotebookAPIMock, httpx.Client]:
    server = NotebookAPIMock()
    client = server.build_httpx_client()
    try:
        yield server, client
    finally:
        client.close()
        server.close()


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "OPEN_NOTEBOOK_SLUG",
        "OPEN_NOTEBOOK_API_BASE",
        "OPEN_NOTEBOOK_API_KEY",
        EXPORT_DIR_ENV,
        EXPORT_MIRROR_ENV,
        "OPEN_NOTEBOOK_AUTO_CREATE",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def reset_auto_create_cache() -> None:
    _reset_auto_create_cache_for_testing()


def test_push_notebook_section_calls_api(
    tmp_path: Path,
    notebook_api_client: tuple[NotebookAPIMock, httpx.Client],
) -> None:
    server, client = notebook_api_client
    slug = "test-notebook"
    os.environ["OPEN_NOTEBOOK_SLUG"] = slug
    os.environ["OPEN_NOTEBOOK_API_BASE"] = server.base_url
    os.environ["OPEN_NOTEBOOK_API_KEY"] = server.token
    payload = push_notebook_section(
        title="Intro",
        content_md="## Section",
        citations=["paper_a"],
        client=OpenNotebookClient(
            OpenNotebookConfig(base_url=server.base_url, api_key=server.token),
            client=client,
        ),
    )

    assert payload["status"] == "ok"
    assert server.notes, "Expected the mock API to receive a request"
    assert "test-notebook" in server.notebooks
    first = server.notes[0]
    assert first["notebook"] == slug
    assert first["content"] == "## Section"
    assert payload["note_id"].startswith(slug)


def test_push_notebook_section_requires_client_type(tmp_path: Path) -> None:
    os.environ["OPEN_NOTEBOOK_SLUG"] = "slug"
    os.environ["OPEN_NOTEBOOK_API_BASE"] = "http://mock-notebook"
    with pytest.raises(ValueError):
        push_notebook_section(title="Bad", content_md="text", client=object())


def test_push_notebook_section_offline_export(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    os.environ[EXPORT_DIR_ENV] = str(export_dir)
    os.environ["OPEN_NOTEBOOK_SLUG"] = "offline-notebook"
    payload = push_notebook_section(
        title="Offline",
        content_md="Content",
    )

    assert payload["status"] == "queued"
    assert payload["reason"] == "offline_export"
    export_path = Path(payload["export_path"])
    assert export_path.exists()
    contents = export_path.read_text(encoding="utf-8").splitlines()
    assert contents, "Expected at least one export entry"
    entry = json.loads(contents[-1])
    assert entry["title"] == "Offline"


def test_push_notebook_section_mirrors_exports(
    tmp_path: Path,
    notebook_api_client: tuple[NotebookAPIMock, httpx.Client],
) -> None:
    server, client = notebook_api_client
    export_dir = tmp_path / "mirror"
    os.environ[EXPORT_DIR_ENV] = str(export_dir)
    os.environ[EXPORT_MIRROR_ENV] = "1"
    os.environ["OPEN_NOTEBOOK_SLUG"] = "mirror-notebook"
    os.environ["OPEN_NOTEBOOK_API_BASE"] = server.base_url
    os.environ["OPEN_NOTEBOOK_API_KEY"] = server.token

    push_notebook_section(
        title="Mirror",
        content_md="Mirrored",
        client=OpenNotebookClient(
            OpenNotebookConfig(base_url=server.base_url, api_key=server.token),
            client=client,
        ),
    )

    assert server.requests, "API should be invoked"
    jsonl = (export_dir / "mirror-notebook.jsonl").read_text(encoding="utf-8")
    assert "Mirrored" in jsonl


def test_push_notebook_section_respects_auto_create_flag(
    notebook_api_client: tuple[NotebookAPIMock, httpx.Client],
) -> None:
    server, client = notebook_api_client
    os.environ["OPEN_NOTEBOOK_AUTO_CREATE"] = "0"
    os.environ["OPEN_NOTEBOOK_SLUG"] = "auto-toggle"
    os.environ["OPEN_NOTEBOOK_API_BASE"] = server.base_url
    os.environ["OPEN_NOTEBOOK_API_KEY"] = server.token

    push_notebook_section(
        title="Auto Toggle",
        content_md="Body",
        client=OpenNotebookClient(
            OpenNotebookConfig(base_url=server.base_url, api_key=server.token),
            client=client,
        ),
    )

    assert "auto-toggle" not in server.notebooks


def test_push_notebook_section_override_auto_create(
    notebook_api_client: tuple[NotebookAPIMock, httpx.Client],
) -> None:
    server, client = notebook_api_client
    os.environ["OPEN_NOTEBOOK_SLUG"] = "override-toggle"
    os.environ["OPEN_NOTEBOOK_API_BASE"] = server.base_url
    os.environ["OPEN_NOTEBOOK_API_KEY"] = server.token

    push_notebook_section(
        title="Override",
        content_md="Body",
        auto_create=False,
        client=OpenNotebookClient(
            OpenNotebookConfig(base_url=server.base_url, api_key=server.token),
            client=client,
        ),
    )

    assert "override-toggle" not in server.notebooks
    assert server.notes, "Section push should still occur"


def test_auto_create_cache_scoped_per_api_base(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_ensure(**kwargs):
        calls.append(kwargs["api_base"])
        return {"status": "created"}

    class FakeClient:
        def push_note(self, notebook_id: str, title: str, content_md: str, citations: list[str]) -> dict:
            return {"status": "ok", "notebook": notebook_id}

    monkeypatch.setattr("apps.codeact.tools.open_notebook.ensure_notebook_exists", fake_ensure)
    _reset_auto_create_cache_for_testing()
    os.environ["OPEN_NOTEBOOK_SLUG"] = "cache-test"
    os.environ["OPEN_NOTEBOOK_API_KEY"] = "token"

    os.environ["OPEN_NOTEBOOK_API_BASE"] = "http://api-one"
    push_notebook_section(title="A", content_md="Body", client=FakeClient())
    assert calls == ["http://api-one"]

    push_notebook_section(title="B", content_md="Body", client=FakeClient())
    assert calls == ["http://api-one"]

    os.environ["OPEN_NOTEBOOK_API_BASE"] = "http://api-two"
    push_notebook_section(title="C", content_md="Body", client=FakeClient())
    assert calls == ["http://api-one", "http://api-two"]


def test_missing_slug_raises_value_error() -> None:
    with pytest.raises(ValueError):
        push_notebook_section(title="Missing", content_md="No slug")



def test_missing_api_base_without_export_dir_uses_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    os.environ["OPEN_NOTEBOOK_SLUG"] = "no-api"
    monkeypatch.delenv("OPEN_NOTEBOOK_API_BASE", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_EXPORT_DIR", raising=False)
    monkeypatch.setenv("COURSEGEN_REPO_ROOT", str(tmp_path))

    response = push_notebook_section(title="Missing API", content_md="No base")

    assert response["status"] == "queued"
    export_path = Path(response["export_path"])
    assert export_path.exists()
    assert export_path.parent == tmp_path / "outputs" / "notebook_exports"
