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
    def __init__(
        self,
        config: OpenNotebookConfig,
        *,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._config = config
        if client is None:
            self._client = httpx.Client(
                base_url=config.base_url,
                timeout=timeout,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def push_note(
        self,
        notebook_id: str,
        title: str,
        content_md: str,
        citations: List[str],
    ) -> Dict[str, Any]:
        """Create a notebook section via the Open Notebook API."""

        payload = {
            "title": title,
            "content": content_md,
            "citations": citations,
        }
        headers = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        response = self._client.post(
            f"/api/notebooks/{notebook_id}/sections",
            json=payload,
            headers=headers or None,
        )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Open Notebook API returned non-JSON payload") from exc

    def close(self) -> None:
        if getattr(self, "_owns_client", False):
            self._client.close()

    def __enter__(self) -> "OpenNotebookClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()
