import logging

import httpx

from app.schemas.callback import AgentCallbackRequest
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    get_request_id,
    get_trace_id,
)

logger = logging.getLogger(__name__)


class CallbackClient:
    def __init__(
        self, callback_url: str, callback_token: str | None = None, timeout: float = 30.0
    ):
        self.callback_url = callback_url
        self.callback_token = callback_token
        self.timeout = timeout

    async def send(self, report: AgentCallbackRequest) -> bool:
        headers = {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }
        if self.callback_token:
            headers["X-Callback-Token"] = self.callback_token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.callback_url,
                    json=report.model_dump(mode="json"),
                    headers=headers,
                )
                if not response.is_success:
                    logger.error(
                        "callback_failed",
                        extra={
                            "status_code": response.status_code,
                            "callback_url": self.callback_url,
                            "response_text": response.text[:500],
                        },
                    )
                return response.is_success
        except httpx.RequestError as e:
            logger.error(
                "callback_request_error",
                extra={
                    "error": str(e),
                    "callback_url": self.callback_url,
                },
            )
            return False
