import httpx

from app.core.settings import get_settings
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)


class ExecutorClient:
    """Client for calling the Executor service."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _trace_headers() -> dict[str, str]:
        return {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }

    async def execute_task(
        self,
        executor_url: str,
        session_id: str,
        run_id: str | None,
        prompt: str,
        callback_url: str,
        callback_token: str,
        config: dict,
        callback_base_url: str | None = None,
        sdk_session_id: str | None = None,
        permission_mode: str = "default",
    ) -> str:
        """Call Executor to execute a task.

        Args:
            executor_url: Executor service URL
            session_id: Session ID
            prompt: Task prompt
            callback_url: Callback URL
            callback_token: Callback token
            config: Task configuration
            callback_base_url: Base URL for callback-related APIs
            sdk_session_id: Claude SDK session ID for resuming conversations
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{executor_url}/v1/tasks/execute",
                json={
                    "session_id": session_id,
                    "run_id": run_id,
                    "prompt": prompt,
                    "callback_url": callback_url,
                    "callback_token": callback_token,
                    "callback_base_url": callback_base_url,
                    "config": config,
                    "sdk_session_id": sdk_session_id,
                    "permission_mode": permission_mode or "default",
                },
                headers=self._trace_headers(),
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
            response.raise_for_status()
            data = response.json()
            return data["session_id"]
