"""Open Notebook helper surfaced to CodeAct tools."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("coursegen.codeact.open_notebook")


def push_notebook_section(
    *,
    notebook_slug: str,
    title: str,
    content_md: str,
    citations: List[str] | None = None,
    api_base: str | None = None,
) -> Dict[str, Any]:
    """Placeholder API call – logs intent and returns a stub response."""
    logger.info(
        "[stub] push_notebook_section title=%s notebook=%s", title, notebook_slug,
        extra={"api_base": api_base},
    )
    return {
        "notebook": notebook_slug,
        "title": title,
        "citations": citations or [],
        "status": "queued",
    }
