"""FastAPI mock for the Open Notebook API used in integration tests."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import anyio
import httpx
from fastapi import FastAPI, Header, HTTPException
from httpx import ASGITransport, BaseTransport
from pydantic import BaseModel, Field
from unittest import mock

class _SyncASGITransport(BaseTransport):
    """Bridge ASGI apps into sync httpx clients."""

    def __init__(self, app: FastAPI) -> None:
        self._asgi = ASGITransport(app=app)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        async def _send() -> tuple[httpx.Response, bytes]:
            response = await self._asgi.handle_async_request(request)
            body = await response.aread()
            await response.aclose()
            return response, body

        response, body = anyio.run(_send)
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            content=body,
            extensions=response.extensions,
            request=request,
        )

    def close(self) -> None:
        anyio.run(self._asgi.aclose)


class NotebookSectionPayload(BaseModel):
    title: str
    content: str
    citations: List[str] = Field(default_factory=list)


class NotebookCreatePayload(BaseModel):
    name: str
    description: Optional[str] = None


class NotebookAPIMock:
    """In-memory FastAPI app that records notes created via the Notebook API."""

    def __init__(
        self,
        *,
        base_url: str = "http://notebook-mock.local",
        token: str = "test-token",
    ) -> None:
        self.base_url = base_url
        self.token = token
        self.app = FastAPI()
        self.notes: List[Dict[str, Any]] = []
        self.requests: List[Dict[str, Any]] = []
        self.notebooks: Dict[str, Dict[str, Any]] = {}
        self._httpx_clients: List[httpx.Client] = []
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app

        @app.post("/api/notebooks/{slug}/sections")
        def create_section(
            slug: str,
            payload: NotebookSectionPayload,
            authorization: Optional[str] = Header(default=None),
        ) -> Dict[str, Any]:
            if self.token and authorization != f"Bearer {self.token}":
                raise HTTPException(status_code=401, detail="invalid token")
            note_id = f"{slug}-{len(self.notes) + 1:04d}"
            record = {
                "note_id": note_id,
                "notebook": slug,
                "title": payload.title,
                "citations": payload.citations,
                "status": "ok",
            }
            self.notes.append(
                {
                    **record,
                    "content": payload.content,
                }
            )
            self.requests.append(
                {
                    "slug": slug,
                    "payload": payload.model_dump(),
                    "authorization": authorization,
                }
            )
            return record

        @app.post("/api/notebooks")
        def create_notebook(
            payload: NotebookCreatePayload,
            authorization: Optional[str] = Header(default=None),
        ) -> Dict[str, Any]:
            if self.token and authorization != f"Bearer {self.token}":
                raise HTTPException(status_code=401, detail="invalid token")
            slug = payload.name.strip()
            if not slug:
                raise HTTPException(status_code=422, detail="notebook name required")
            if slug in self.notebooks:
                raise HTTPException(status_code=409, detail="notebook exists")
            record = {
                "status": "created",
                "notebook": slug,
            }
            if payload.description:
                record["description"] = payload.description
            self.notebooks[slug] = record
            return record

    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.notes.clear()
        self.requests.clear()
        self.notebooks.clear()

    def build_httpx_client(self, *, timeout: float = 5.0) -> httpx.Client:
        client = httpx.Client(
            base_url=self.base_url,
            transport=_SyncASGITransport(app=self.app),
            timeout=timeout,
        )
        self._httpx_clients.append(client)
        return client

    def close(self) -> None:
        for client in self._httpx_clients:
            client.close()
        self._httpx_clients.clear()

    @contextmanager
    def patch_open_notebook_client(self):
        """Patch push_notebook_section to route requests through the FastAPI app."""

        mock_server = self

        class _PatchedOpenNotebookClient:
            def __init__(
                self,
                config,
                *,
                client: httpx.Client | None = None,
                timeout: float = 30.0,
            ) -> None:
                self._config = config
                self._client = client or mock_server.build_httpx_client(timeout=timeout)
                self._owns_client = client is None

            def _headers(self) -> Dict[str, str] | None:
                if not self._config.api_key:
                    return None
                return {"Authorization": f"Bearer {self._config.api_key}"}

            def push_note(
                self,
                notebook_id: str,
                title: str,
                content_md: str,
                citations: List[str],
            ) -> Dict[str, Any]:
                payload = {
                    "title": title,
                    "content": content_md,
                    "citations": citations,
                }
                response = self._client.post(
                    f"/api/notebooks/{notebook_id}/sections",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()

            def ensure_notebook(
                self,
                notebook_id: str,
                *,
                description: str | None = None,
            ) -> Dict[str, Any]:
                payload: Dict[str, Any] = {"name": notebook_id}
                if description:
                    payload["description"] = description
                response = self._client.post(
                    "/api/notebooks",
                    json=payload,
                    headers=self._headers(),
                )
                if response.status_code == 409:
                    return {"status": "exists", "notebook": notebook_id}
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    data.setdefault("notebook", notebook_id)
                return data

            def close(self) -> None:
                if self._owns_client:
                    self._client.close()

        patcher = mock.patch(
            "apps.codeact.tools.open_notebook.OpenNotebookClient",
            _PatchedOpenNotebookClient,
        )
        patcher.start()
        try:
            yield self
        finally:
            patcher.stop()


__all__ = ["NotebookAPIMock", "NotebookSectionPayload"]
