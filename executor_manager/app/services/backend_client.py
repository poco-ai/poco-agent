import asyncio
from typing import Any

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)


class BackendClient:
    """Client for communicating with the Backend service."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (self.settings.backend_url or "").rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
            timeout=httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0),
            trust_env=False,
        )

    @staticmethod
    def _trace_headers() -> dict[str, str]:
        # When called from an HTTP request handler, these come from middleware context.
        return {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        retry_connect_errors: int = 0,
        **kwargs: Any,
    ) -> httpx.Response:
        attempt = 0
        while True:
            try:
                response = await self._client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt >= retry_connect_errors:
                    raise
                attempt += 1
                await asyncio.sleep(min(0.25 * attempt, 1.0))

    async def create_session(self, user_id: str, config: dict) -> dict:
        """Create a session, returns session info dict with session_id and sdk_session_id."""
        response = await self._request(
            "POST",
            "/api/v1/internal/sessions",
            json={"config": config},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data["data"]

    async def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        await self._request(
            "PATCH",
            f"/api/v1/internal/sessions/{session_id}/status",
            json={"status": status},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )

    async def get_session(self, session_id: str) -> dict:
        """Fetch session details from Backend internal API."""
        response = await self._request(
            "GET",
            f"/api/v1/internal/sessions/{session_id}",
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def forward_callback(self, callback_data: dict) -> dict[str, Any]:
        """Forward Executor callback to Backend and return the callback response."""
        response = await self._request(
            "POST",
            "/api/v1/callback",
            json=callback_data,
            headers=self._trace_headers(),
            retry_connect_errors=3,
        )
        data = response.json()
        result = data.get("data", {})
        return result if isinstance(result, dict) else {}

    async def dispatch_due_agent_assignments(self, *, limit: int) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/v1/internal/agent-assignments/dispatch-due",
            json={"limit": limit},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )
        data = response.json()
        result = data.get("data", {})
        return result if isinstance(result, dict) else {}

    async def claim_run(
        self,
        worker_id: str,
        lease_seconds: int = 30,
        schedule_modes: list[str] | None = None,
    ) -> dict | None:
        """Claim next run from backend queue."""
        payload: dict = {"worker_id": worker_id, "lease_seconds": lease_seconds}
        if schedule_modes:
            payload["schedule_modes"] = schedule_modes

        response = await self._request(
            "POST",
            "/api/v1/runs/claim",
            json=payload,
            headers=self._trace_headers(),
            retry_connect_errors=2,
        )
        data = response.json()
        return data.get("data")

    async def start_run(self, run_id: str, worker_id: str) -> dict:
        """Mark run as running."""
        response = await self._request(
            "POST",
            f"/api/v1/runs/{run_id}/start",
            json={"worker_id": worker_id},
            headers=self._trace_headers(),
            retry_connect_errors=2,
        )
        data = response.json()
        return data["data"]

    async def fail_run(
        self, run_id: str, worker_id: str, error_message: str | None = None
    ) -> dict:
        """Mark run as failed."""
        response = await self._request(
            "POST",
            f"/api/v1/runs/{run_id}/fail",
            json={"worker_id": worker_id, "error_message": error_message},
            headers=self._trace_headers(),
            retry_connect_errors=2,
        )
        data = response.json()
        return data["data"]

    async def claim_session_cancellation(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
    ) -> dict | None:
        """Claim the next pending session cancellation for this worker."""
        response = await self._request(
            "POST",
            "/api/v1/internal/sessions/cancellations/claim",
            json={"worker_id": worker_id, "lease_seconds": lease_seconds},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )
        data = response.json()
        return data.get("data")

    async def complete_session_cancellation(
        self,
        *,
        session_id: str,
        worker_id: str,
        stop_status: str,
        message: str | None = None,
    ) -> dict:
        """Acknowledge session cancellation handling back to Backend."""
        response = await self._request(
            "POST",
            f"/api/v1/internal/sessions/{session_id}/cancellation-complete",
            json={
                "worker_id": worker_id,
                "stop_status": stop_status,
                "message": message,
            },
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )
        data = response.json()
        return data["data"]

    async def get_env_map(self, user_id: str) -> dict[str, str]:
        response = await self._request(
            "GET",
            "/api/v1/internal/env-vars/map",
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def resolve_mcp_config(self, user_id: str, server_ids: list[int]) -> dict:
        """Resolve effective MCP config for execution based on selected server ids."""
        response = await self._request(
            "POST",
            "/api/v1/internal/mcp-config/resolve",
            json={"server_ids": server_ids},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def resolve_skill_config(self, user_id: str, skill_ids: list[int]) -> dict:
        """Resolve effective skill config for execution based on selected skill ids."""
        response = await self._request(
            "POST",
            "/api/v1/internal/skill-config/resolve",
            json={"skill_ids": skill_ids},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def resolve_plugin_config(self, user_id: str, plugin_ids: list[int]) -> dict:
        """Resolve effective plugin config for execution based on selected plugin ids."""
        response = await self._request(
            "POST",
            "/api/v1/internal/plugin-config/resolve",
            json={"plugin_ids": plugin_ids},
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def resolve_subagents(
        self, user_id: str, subagent_ids: list[int] | None
    ) -> dict:
        """Resolve enabled subagents for execution based on selected ids.

        When `subagent_ids` is None, backend uses the user's enabled subagents
        as defaults. An explicit empty list means "disable all subagents".
        """
        payload: dict = {}
        if subagent_ids is not None:
            payload["subagent_ids"] = subagent_ids
        response = await self._request(
            "POST",
            "/api/v1/internal/subagents/resolve",
            json=payload,
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def resolve_slash_commands(
        self,
        user_id: str,
        names: list[str] | None = None,
        skill_names: list[str] | None = None,
    ) -> dict[str, str]:
        """Resolve enabled slash commands for execution (rendered markdown)."""
        payload: dict = {"names": names or []}
        if skill_names is not None:
            payload["skill_names"] = skill_names
        response = await self._request(
            "POST",
            "/api/v1/internal/slash-commands/resolve",
            json=payload,
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                "X-User-Id": user_id,
                **self._trace_headers(),
            },
        )
        data = response.json()
        resolved = data.get("data", {}) or {}
        if not isinstance(resolved, dict):
            return {}
        return {str(k): str(v) for k, v in resolved.items() if isinstance(v, str)}

    async def get_preset(self, user_id: str, preset_id: int) -> dict[str, Any]:
        try:
            response = await self._request(
                "GET",
                f"/api/v1/presets/{preset_id}",
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Preset not found: {preset_id}",
                ) from exc
            raise
        data = response.json()
        result = data.get("data", {}) or {}
        return result if isinstance(result, dict) else {}

    async def get_claude_md(self, user_id: str) -> dict:
        """Fetch user-level CLAUDE.md settings for execution staging."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/claude-md",
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("data", {}) or {}
            return result if isinstance(result, dict) else {}

    async def dispatch_due_scheduled_tasks(self, limit: int = 50) -> dict:
        """Trigger backend to dispatch due scheduled tasks into the run queue."""
        payload = {"limit": max(1, int(limit))}
        response = await self._request(
            "POST",
            "/api/v1/internal/scheduled-tasks/dispatch-due",
            json=payload,
            headers={
                "X-Internal-Token": self.settings.internal_api_token,
                **self._trace_headers(),
            },
            retry_connect_errors=2,
        )
        data = response.json()
        return data.get("data", {}) or {}

    async def create_user_input_request(self, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/user-input-requests",
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]

    async def get_user_input_request(self, request_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/user-input-requests/{request_id}",
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]

    async def create_memory(self, session_id: str, payload: dict[str, Any]) -> Any:
        """Create memories via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/memories",
                params={"session_id": session_id},
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def get_memory_create_job(self, session_id: str, job_id: str) -> Any:
        """Get memory create job status via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/memories/jobs/{job_id}",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def list_memories(self, session_id: str) -> Any:
        """List memories via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/memories",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def search_memories(self, session_id: str, payload: dict[str, Any]) -> Any:
        """Search memories via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/memories/search",
                params={"session_id": session_id},
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def get_memory(self, session_id: str, memory_id: str) -> Any:
        """Get a memory by id via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/memories/{memory_id}",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def update_memory(
        self,
        session_id: str,
        memory_id: str,
        payload: dict[str, Any],
    ) -> Any:
        """Update a memory by id via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/api/v1/internal/memories/{memory_id}",
                params={"session_id": session_id},
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def get_memory_history(self, session_id: str, memory_id: str) -> Any:
        """Get memory history via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/memories/{memory_id}/history",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def delete_memory(self, session_id: str, memory_id: str) -> dict[str, Any]:
        """Delete a memory by id via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/internal/memories/{memory_id}",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("data")
            return result if isinstance(result, dict) else {}

    async def delete_all_memories(self, session_id: str) -> dict[str, Any]:
        """Delete all memories in session scope via backend internal API."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/internal/memories",
                params={"session_id": session_id},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("data")
            return result if isinstance(result, dict) else {}
