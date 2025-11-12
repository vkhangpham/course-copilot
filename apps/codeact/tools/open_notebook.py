"""Open Notebook helper surfaced to CodeAct tools."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from apps.codeact.tools_open_notebook import OpenNotebookClient as _OpenNotebookClient, OpenNotebookConfig

_REAL_OPEN_NOTEBOOK_CLIENT = _OpenNotebookClient
OpenNotebookClient = _OpenNotebookClient

logger = logging.getLogger("coursegen.codeact.open_notebook")

EXPORT_DIR_ENV = "OPEN_NOTEBOOK_EXPORT_DIR"
EXPORT_MIRROR_ENV = "OPEN_NOTEBOOK_EXPORT_MIRROR"
DEFAULT_EXPORT_DIR = Path("outputs/notebook_exports")
AUTO_CREATE_ENV = "OPEN_NOTEBOOK_AUTO_CREATE"


_ENSURED_NOTEBOOKS: set[tuple[str, str]] = set()


def _supports_push_notebook(instance: object) -> bool:
    if isinstance(instance, _REAL_OPEN_NOTEBOOK_CLIENT):
        return True
    push = getattr(instance, "push_note", None)
    return callable(push)


def _supports_ensure_notebook(instance: object) -> bool:
    if isinstance(instance, _REAL_OPEN_NOTEBOOK_CLIENT):
        return True
    ensure = getattr(instance, "ensure_notebook", None)
    return callable(ensure)


def _export_dir_configured() -> bool:
    raw = os.getenv(EXPORT_DIR_ENV)
    return bool(raw and raw.strip())


def _cache_key(base_url: str, slug: str) -> tuple[str, str]:
    return (base_url.rstrip("/"), slug.strip().lower())


def ensure_notebook_exists(
    *,
    notebook_slug: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    description: str | None = None,
    client: object | None = None,
) -> Dict[str, Any]:
    """Create the notebook if it is missing and return the API response."""

    slug = (notebook_slug or os.getenv("OPEN_NOTEBOOK_SLUG") or "").strip()
    if not slug:
        raise ValueError("Notebook slug required (set OPEN_NOTEBOOK_SLUG or pass notebook_slug)")

    base_url = (api_base or os.getenv("OPEN_NOTEBOOK_API_BASE") or "").strip()
    token = api_key or os.getenv("OPEN_NOTEBOOK_API_KEY")

    if not base_url:
        raise ValueError(
            "Open Notebook API base required (set OPEN_NOTEBOOK_API_BASE or pass api_base) "
            "to create notebooks."
        )

    cache_key = _cache_key(base_url, slug)
    config = OpenNotebookConfig(base_url=base_url, api_key=token)
    owns_client = False
    if client is None:
        client = OpenNotebookClient(config)
        owns_client = True
    if not _supports_ensure_notebook(client):
        logger.debug(
            "Skipping notebook auto-create; client lacks ensure_notebook",
            extra={"client": type(client).__name__, "notebook": slug},
        )
        if owns_client:
            client.close()
        return {"status": "skipped", "reason": "client_missing_ensure", "notebook": slug}
    try:
        result = client.ensure_notebook(slug, description=description)
        _ENSURED_NOTEBOOKS.add(cache_key)
        logger.info(
            "ensure_notebook_exists succeeded",
            extra={"notebook": slug, "api_base": base_url},
        )
        return result
    finally:
        if owns_client:
            client.close()


def push_notebook_section(
    *,
    notebook_slug: str | None = None,
    title: str,
    content_md: str,
    citations: List[str] | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    client: object | None = None,
    auto_create: bool | None = None,
) -> Dict[str, Any]:
    """Send a markdown section to the configured Open Notebook instance."""

    slug = (notebook_slug or os.getenv("OPEN_NOTEBOOK_SLUG") or "").strip()
    if not slug:
        raise ValueError("Notebook slug required (set OPEN_NOTEBOOK_SLUG or pass notebook_slug)")

    base_url = (api_base or os.getenv("OPEN_NOTEBOOK_API_BASE") or "").strip()
    token = api_key or os.getenv("OPEN_NOTEBOOK_API_KEY")
    payload_citations = list(citations or [])

    if not base_url:
        if not _export_dir_configured():
            raise ValueError(
                "Open Notebook API base required (set OPEN_NOTEBOOK_API_BASE or pass api_base). "
                "To run offline, set OPEN_NOTEBOOK_EXPORT_DIR to opt into local exports."
            )
        return _persist_stub_export(
            notebook_slug=slug,
            title=title,
            content_md=content_md,
            citations=payload_citations,
        )

    cache_key = _cache_key(base_url, slug)
    config = OpenNotebookConfig(base_url=base_url, api_key=token)
    owns_client = False
    if client is None:
        client = OpenNotebookClient(config)
        owns_client = True
    elif not _supports_push_notebook(client):
        raise ValueError("client must be an OpenNotebookClient instance")
    try:
        need_preflight = _auto_create_enabled(auto_create) and cache_key not in _ENSURED_NOTEBOOKS
        if need_preflight:
            if client is not None and not _supports_ensure_notebook(client):
                logger.debug(
                    "Skipping notebook auto-create; client lacks ensure_notebook",
                    extra={"client": type(client).__name__, "notebook": slug},
                )
            else:
                ensure_notebook_exists(
                    notebook_slug=slug,
                    api_base=base_url,
                    api_key=token,
                    client=client,
                )
                _ENSURED_NOTEBOOKS.add(cache_key)
        response = client.push_note(
            slug,
            title,
            content_md,
            payload_citations,
        )
        logger.info(
            "push_notebook_section succeeded",
            extra={"notebook": slug, "api_base": base_url},
        )
        if _should_mirror_exports():
            _persist_stub_export(
                notebook_slug=slug,
                title=title,
                content_md=content_md,
                citations=payload_citations,
            )
        return response
    finally:
        if owns_client:
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


def _auto_create_enabled(override: bool | None = None) -> bool:
    if override is not None:
        return bool(override)
    flag = os.getenv(AUTO_CREATE_ENV)
    if not flag:
        return True
    return flag.strip().lower() not in {"0", "false", "no", "off"}


def _reset_auto_create_cache_for_testing() -> None:  # pragma: no cover - test helper
    _ENSURED_NOTEBOOKS.clear()
