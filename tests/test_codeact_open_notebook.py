import json
from pathlib import Path

from apps.codeact.tools.open_notebook import push_notebook_section


def test_push_notebook_section_persists_stub_when_api_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("OPEN_NOTEBOOK_API_BASE", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_API_KEY", raising=False)
    monkeypatch.setenv("OPEN_NOTEBOOK_EXPORT_DIR", str(tmp_path))

    result = push_notebook_section(
        notebook_slug="DB-PoC",
        title="Week 1",
        content_md="**content**",
        citations=["codd-1970"],
    )

    export_path = Path(result["export_path"])
    assert export_path.exists()
    lines = export_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["title"] == "Week 1"
    assert entry["citations"] == ["codd-1970"]
    assert entry["notebook"] == "DB-PoC"


def test_push_notebook_section_appends_stub_entries(monkeypatch, tmp_path):
    monkeypatch.delenv("OPEN_NOTEBOOK_API_BASE", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_API_KEY", raising=False)
    monkeypatch.setenv("OPEN_NOTEBOOK_EXPORT_DIR", str(tmp_path))

    push_notebook_section(
        notebook_slug="db-poc",
        title="Intro",
        content_md="A",
        citations=[],
    )
    push_notebook_section(
        notebook_slug="db-poc",
        title="Transactions",
        content_md="B",
        citations=["aries"],
    )

    export_path = tmp_path / "db-poc.jsonl"
    lines = export_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["title"] == "Transactions"


def test_push_notebook_section_calls_api_when_base(monkeypatch, tmp_path):
    calls = []

    class FakeClient:
        def __init__(self, config):
            self.config = config

        def push_note(self, notebook_slug, title, content_md, citations):
            calls.append((notebook_slug, title, content_md, citations, self.config.base_url))
            return {"ok": True}

        def close(self):
            calls.append(("closed",))

    monkeypatch.setattr(
        "apps.codeact.tools.open_notebook.OpenNotebookClient",
        FakeClient,
    )
    monkeypatch.setenv("OPEN_NOTEBOOK_EXPORT_DIR", str(tmp_path))

    result = push_notebook_section(
        notebook_slug="db-poc",
        title="Week 3",
        content_md="Distributed systems",
        citations=["spanner"],
        api_base="http://localhost:5055",
        api_key="token",
    )

    assert result == {"ok": True}
    assert calls[0][:4] == (
        "db-poc",
        "Week 3",
        "Distributed systems",
        ["spanner"],
    )
    assert calls[0][4] == "http://localhost:5055"
    assert calls[-1] == ("closed",)
    export_path = tmp_path / "db-poc.jsonl"
    assert not export_path.exists()
