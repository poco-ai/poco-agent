import asyncio
import logging
import os

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
        self,
        callback_url: str,
        callback_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        initial_backoff_seconds: float = 0.5,
        max_backoff_seconds: float = 2.0,
    ):
        self.callback_url = callback_url
        self.callback_token = (
            callback_token
            or os.environ.get("POCO_CALLBACK_TOKEN")
            or os.environ.get("CALLBACK_TOKEN")
            or ""
        ).strip()
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.initial_backoff_seconds = max(0.0, initial_backoff_seconds)
        self.max_backoff_seconds = max(
            self.initial_backoff_seconds, max_backoff_seconds
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "X-Request-ID": get_request_id() or generate_request_id(),
            "X-Trace-ID": get_trace_id() or generate_trace_id(),
        }
        if self.callback_token:
            headers["Authorization"] = f"Bearer {self.callback_token}"
        return headers

    @staticmethod
    def _is_retriable_status(status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    async def send(self, report: AgentCallbackRequest) -> bool:
        total_attempts = self.max_retries + 1
        payload = report.model_dump(mode="json")
        context = {
            "session_id": report.session_id,
            "run_id": report.run_id,
            "callback_status": report.status,
        }

        for attempt_index in range(total_attempts):
            attempt_number = attempt_index + 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.callback_url,
                        json=payload,
                        headers=self._build_headers(),
                    )
            except httpx.RequestError as exc:
                if attempt_number < total_attempts:
                    backoff_seconds = min(
                        self.initial_backoff_seconds * (2**attempt_index),
                        self.max_backoff_seconds,
                    )
                    logger.warning(
                        "callback_delivery_retry_scheduled",
                        extra={
                            **context,
                            "attempt": attempt_number,
                            "max_attempts": total_attempts,
                            "backoff_seconds": backoff_seconds,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(backoff_seconds)
                    continue

                logger.error(
                    "callback_delivery_failed",
                    extra={
                        **context,
                        "attempt": attempt_number,
                        "max_attempts": total_attempts,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                return False

            if response.is_success:
                if attempt_number > 1:
                    logger.info(
                        "callback_delivery_recovered",
                        extra={
                            **context,
                            "attempt": attempt_number,
                            "max_attempts": total_attempts,
                            "status_code": response.status_code,
                        },
                    )
                return True

            response_context = {
                **context,
                "attempt": attempt_number,
                "max_attempts": total_attempts,
                "status_code": response.status_code,
            }
            if (
                self._is_retriable_status(response.status_code)
                and attempt_number < total_attempts
            ):
                backoff_seconds = min(
                    self.initial_backoff_seconds * (2**attempt_index),
                    self.max_backoff_seconds,
                )
                logger.warning(
                    "callback_delivery_retry_scheduled",
                    extra={
                        **response_context,
                        "backoff_seconds": backoff_seconds,
                    },
                )
                await asyncio.sleep(backoff_seconds)
                continue

            logger.error("callback_delivery_failed", extra=response_context)
            return False

        return False
