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
        notebook_record_id: str | None = None,
    ) -> Dict[str, Any]:
        """Create a notebook section via the Open Notebook API."""

        payload = {
            "title": title,
            "content": content_md,
            "citations": citations,
        }
        response = self._client.post(
            f"/api/notebooks/{notebook_id}/sections",
            json=payload,
            headers=self._build_headers(),
        )
        if response.status_code == 404:
            return self._post_note_fallback(
                notebook_record_id or notebook_id,
                title,
                content_md,
                citations,
            )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Open Notebook API returned non-JSON payload") from exc
        if isinstance(data, dict):
            data.setdefault("status", "ok")
            data.setdefault("note_id", data.get("id"))
            data.setdefault("notebook", notebook_id)
        return data

    def _post_note_fallback(
        self,
        notebook_id: str,
        title: str,
        content_md: str,
        citations: List[str],
    ) -> Dict[str, Any]:
        """Fallback path for stacks that expose only /api/notes endpoints."""

        payload = {
            "title": title,
            "content": _append_citations_block(content_md, citations),
            "note_type": "ai",
            "notebook_id": notebook_id,
        }
        response = self._client.post(
            "/api/notes",
            json=payload,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Open Notebook API returned non-JSON payload") from exc
        if not isinstance(data, dict):
            return {"status": "ok", "notebook": notebook_id, "note": data}
        data.setdefault("status", "ok")
        data.setdefault("note_id", data.get("id"))
        data.setdefault("notebook", notebook_id)
        return data

    def ensure_notebook(
        self,
        notebook_id: str,
        *,
        description: str | None = None,
    ) -> Dict[str, Any]:
        """Create the target notebook if it does not exist."""

        payload: Dict[str, Any] = {"name": notebook_id}
        if description:
            payload["description"] = description

        response = self._client.post(
            "/api/notebooks",
            json=payload,
            headers=self._build_headers(),
        )
        if response.status_code == 409:
            return {"status": "exists", "notebook": notebook_id}
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {"status": "ok", "notebook": notebook_id}
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Open Notebook API returned non-JSON payload") from exc
        if isinstance(data, dict):
            data.setdefault("notebook", notebook_id)
        return data

    def list_notebooks(self) -> List[Dict[str, Any]]:
        """Return notebooks exposed by the remote API (best effort)."""

        response = self._client.get(
            "/api/notebooks",
            headers=self._build_headers(),
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("Open Notebook API returned non-JSON payload") from exc
        return data if isinstance(data, list) else []

    def close(self) -> None:
        if getattr(self, "_owns_client", False):
            self._client.close()

    def _build_headers(self) -> Dict[str, str] | None:
        if not self._config.api_key:
            return None
        return {"Authorization": f"Bearer {self._config.api_key}"}

    def __enter__(self) -> "OpenNotebookClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()


def _append_citations_block(content: str, citations: List[str]) -> str:
    if not citations:
        return content
    cleaned = [cite.strip() for cite in citations if cite and cite.strip()]
    if not cleaned:
        return content
    lines = [content.rstrip(), "", "## Citations"]
    lines.extend(f"- {cite}" for cite in cleaned)
    return "\n".join(lines)
