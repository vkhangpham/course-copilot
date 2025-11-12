"""Open Notebook helper surfaced to CodeAct tools."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from apps.codeact.tools_open_notebook import OpenNotebookClient, OpenNotebookConfig

logger = logging.getLogger("coursegen.codeact.open_notebook")

EXPORT_DIR_ENV = "OPEN_NOTEBOOK_EXPORT_DIR"
EXPORT_MIRROR_ENV = "OPEN_NOTEBOOK_EXPORT_MIRROR"
DEFAULT_EXPORT_DIR = Path("outputs/notebook_exports")


def push_notebook_section(
    *,
    notebook_slug: str,
    title: str,
    content_md: str,
    citations: List[str] | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Send a markdown section to the configured Open Notebook instance."""

    base_url = api_base or os.getenv("OPEN_NOTEBOOK_API_BASE")
    token = api_key or os.getenv("OPEN_NOTEBOOK_API_KEY")
    payload_citations = list(citations or [])

    if not base_url:
        return _persist_stub_export(
            notebook_slug=notebook_slug,
            title=title,
            content_md=content_md,
            citations=payload_citations,
        )

    config = OpenNotebookConfig(base_url=base_url, api_key=token)
    client = OpenNotebookClient(config)
    try:
        response = client.push_note(
            notebook_slug,
            title,
            content_md,
            payload_citations,
        )
        logger.info(
            "push_notebook_section succeeded",
            extra={"notebook": notebook_slug, "api_base": base_url},
        )
        if _should_mirror_exports():
            _persist_stub_export(
                notebook_slug=notebook_slug,
                title=title,
                content_md=content_md,
                citations=payload_citations,
            )
        return response
    finally:
        client.close()


def _persist_stub_export(
    *,
    notebook_slug: str,
    title: str,
    content_md: str,
    citations: List[str],
) -> Dict[str, Any]:
    export_dir = _resolve_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"{_sanitize_slug(notebook_slug)}.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notebook": notebook_slug,
        "title": title,
        "content": content_md,
        "citations": citations,
    }
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info(
        "push_notebook_section persisted locally",
        extra={"notebook": notebook_slug, "export_path": str(export_path)},
    )
    return {
        "status": "queued",
        "notebook": notebook_slug,
        "export_path": str(export_path),
        "entry": record,
    }


def _resolve_export_dir() -> Path:
    raw = os.getenv(EXPORT_DIR_ENV)
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_EXPORT_DIR.expanduser().resolve()


def _sanitize_slug(value: str | None) -> str:
    if not value:
        return "notebook"
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or "notebook"


def _should_mirror_exports() -> bool:
    flag = os.getenv(EXPORT_MIRROR_ENV)
    if not flag:
        return False
    return flag.strip().lower() in {"1", "true", "yes", "on"}
