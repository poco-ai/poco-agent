import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one concise line per request (method/path/status/duration)."""

    def __init__(self, app, *, skip_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self._skip_paths = skip_paths or {"/api/v1/health", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._skip_paths:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        status = response.status_code
        level = logging.INFO
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING

        logger.log(
            level,
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": duration_ms,
            },
        )
        return response
