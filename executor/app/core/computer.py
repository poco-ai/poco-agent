import logging

import httpx  # pyrefly: ignore[missing-import]

from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)

logger = logging.getLogger(__name__)


class ComputerClient:
    """Client for sending Poco Computer artifacts to Executor Manager."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def upload_browser_screenshot(
        self,
        *,
        session_id: str,
        run_id: str | None,
        tool_use_id: str,
        png_bytes: bytes,
    ) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/computer/screenshots",
                    data={
                        "session_id": session_id,
                        "run_id": run_id or "",
                        "tool_use_id": tool_use_id,
                    },
                    files={
                        "file": ("screenshot.png", png_bytes, "image/png"),
                    },
                    headers={
                        "X-Request-ID": get_request_id() or generate_request_id(),
                        "X-Trace-ID": get_trace_id() or generate_trace_id(),
                    },
                )
                if not response.is_success:
                    logger.warning(
                        "computer_screenshot_upload_failed",
                        extra={
                            "session_id": session_id,
                            "tool_use_id": tool_use_id,
                            "status_code": response.status_code,
                            "response_text": response.text[:300],
                        },
                    )
                return response.is_success
        except httpx.RequestError:
            return False
