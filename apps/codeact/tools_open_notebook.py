"""HTTP client wrappers for Open Notebook."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import httpx


@dataclass
class OpenNotebookConfig:
    base_url: str
    api_key: str | None = None


class OpenNotebookClient:
    def __init__(self, config: OpenNotebookConfig):
        self._config = config
        self._client = httpx.Client(base_url=config.base_url, timeout=30)

    def push_note(
        self,
        notebook_id: str,
        title: str,
        content_md: str,
        citations: List[str],
    ) -> Dict[str, Any]:  # pragma: no cover - placeholder
        raise NotImplementedError("Open Notebook wiring will be added once API credentials are set.")
