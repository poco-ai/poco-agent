import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)


class UserInputClient:
    def __init__(
        self,
        base_url: str,
        callback_token: str = "",
        timeout: float = 10.0,
        poll_interval: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.callback_token = callback_token
        self.timeout = timeout
        self.poll_interval = poll_interval

    @staticmethod
    def resolve_base_url(callback_url: str, callback_base_url: str | None) -> str:
        if callback_base_url:
            return callback_base_url.rstrip("/")
        if callback_url.endswith("/api/v1/callback"):
            return callback_url[: -len("/api/v1/callback")]
        return callback_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }
        if self.callback_token:
            headers["Authorization"] = f"Bearer {self.callback_token}"
        return headers

    async def create_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/user-input-requests",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})

    async def get_request(self, request_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/user-input-requests/{request_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})

    async def wait_for_answer(
        self, request_id: str, timeout_seconds: float = 60
    ) -> dict[str, Any] | None:
        deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
        while datetime.now(timezone.utc).timestamp() < deadline:
            payload = await self.get_request(request_id)
            status = payload.get("status")
            if status == "answered":
                return payload
            if status == "expired":
                return None
            await asyncio.sleep(self.poll_interval)
        return None
