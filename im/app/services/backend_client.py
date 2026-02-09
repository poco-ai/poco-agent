import logging
from typing import Any

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class BackendClientError(RuntimeError):
    pass


class BackendClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.backend_url.rstrip("/")
        self.backend_user_id = (
            self.settings.backend_user_id or "default"
        ).strip() or "default"
        self.timeout = httpx.Timeout(
            self.settings.poll_http_timeout_seconds,
            connect=min(10.0, self.settings.poll_http_timeout_seconds),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers={"X-User-Id": self.backend_user_id},
            )

        # Backend always returns JSON with {code,message,data} on success/error, but
        # still validate status code first for transport errors.
        if resp.status_code < 200 or resp.status_code >= 300:
            raise BackendClientError(
                f"Backend HTTP {resp.status_code}: {resp.text[:300]}"
            )

        payload = resp.json()
        if not isinstance(payload, dict):
            raise BackendClientError("Backend response is not a JSON object")

        code = payload.get("code")
        if code not in (0, 200):
            raise BackendClientError(
                f"Backend error code={code} message={payload.get('message')!r}"
            )
        return payload.get("data")

    async def enqueue_task(
        self,
        *,
        prompt: str,
        session_id: str | None = None,
        project_id: str | None = None,
        config: dict[str, Any] | None = None,
        permission_mode: str = "default",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "prompt": prompt,
            "session_id": session_id,
            "project_id": project_id,
            "config": config,
            "permission_mode": permission_mode,
            "schedule_mode": "immediate",
        }
        return await self._request("POST", "/tasks", json=body)

    async def list_sessions(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        kind: str = "chat",
    ) -> list[dict[str, Any]]:
        params = {"limit": limit, "offset": offset, "kind": kind}
        data = await self._request("GET", "/sessions", params=params)
        if not isinstance(data, list):
            return []
        return data

    async def get_session_state(self, *, session_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/sessions/{session_id}/state")
        return data if isinstance(data, dict) else {}

    async def list_runs_by_session(self, *, session_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/runs/session/{session_id}")
        if not isinstance(data, list):
            return []
        return data

    async def list_user_input_requests(
        self, *, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        params = {"session_id": session_id} if session_id else None
        data = await self._request("GET", "/user-input-requests", params=params)
        if not isinstance(data, list):
            return []
        return data

    async def answer_user_input_request(
        self, *, request_id: str, answers: dict[str, str]
    ) -> dict[str, Any]:
        body = {"answers": answers}
        data = await self._request(
            "POST", f"/user-input-requests/{request_id}/answer", json=body
        )
        return data if isinstance(data, dict) else {}
