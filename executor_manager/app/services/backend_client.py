import httpx

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
        self.base_url = self.settings.backend_url

    @staticmethod
    def _trace_headers() -> dict[str, str]:
        # When called from an HTTP request handler, these come from middleware context.
        return {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }

    async def create_session(self, user_id: str, config: dict) -> dict:
        """Create a session, returns session info dict with session_id and sdk_session_id."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/sessions",
                json={"user_id": user_id, "config": config},
                headers=self._trace_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]

    async def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                json={"status": status},
                headers=self._trace_headers(),
            )
            response.raise_for_status()

    async def forward_callback(self, callback_data: dict) -> None:
        """Forward Executor callback to Backend."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/callback",
                json=callback_data,
                headers=self._trace_headers(),
            )
            response.raise_for_status()

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

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/runs/claim",
                json=payload,
                headers=self._trace_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data")

    async def start_run(self, run_id: str, worker_id: str) -> dict:
        """Mark run as running."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/runs/{run_id}/start",
                json={"worker_id": worker_id},
                headers=self._trace_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]

    async def fail_run(
        self, run_id: str, worker_id: str, error_message: str | None = None
    ) -> dict:
        """Mark run as failed."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/runs/{run_id}/fail",
                json={"worker_id": worker_id, "error_message": error_message},
                headers=self._trace_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]

    async def get_env_map(self, user_id: str) -> dict[str, str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/internal/env-vars/map",
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}) or {}

    async def resolve_mcp_config(self, user_id: str, server_ids: list[int]) -> dict:
        """Resolve effective MCP config for execution based on selected server ids."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/mcp-config/resolve",
                json={"server_ids": server_ids},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}) or {}

    async def resolve_skill_config(self, user_id: str, skill_ids: list[int]) -> dict:
        """Resolve effective skill config for execution based on selected skill ids."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/skill-config/resolve",
                json={"skill_ids": skill_ids},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}) or {}

    async def resolve_plugin_config(self, user_id: str, plugin_ids: list[int]) -> dict:
        """Resolve effective plugin config for execution based on selected plugin ids."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/plugin-config/resolve",
                json={"plugin_ids": plugin_ids},
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/subagents/resolve",
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/slash-commands/resolve",
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    "X-User-Id": user_id,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
            data = response.json()
            resolved = data.get("data", {}) or {}
            if not isinstance(resolved, dict):
                return {}
            return {str(k): str(v) for k, v in resolved.items() if isinstance(v, str)}

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/internal/scheduled-tasks/dispatch-due",
                json=payload,
                headers={
                    "X-Internal-Token": self.settings.internal_api_token,
                    **self._trace_headers(),
                },
            )
            response.raise_for_status()
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
