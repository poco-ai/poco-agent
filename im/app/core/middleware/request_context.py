import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
    set_request_id,
    set_trace_id,
)

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = (
            request.headers.get(REQUEST_ID_HEADER) or ""
        ).strip() or generate_request_id()
        trace_id = (
            request.headers.get(TRACE_ID_HEADER) or ""
        ).strip() or generate_trace_id()

        set_request_id(req_id)
        set_trace_id(trace_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = req_id
        response.headers[TRACE_ID_HEADER] = trace_id
        return response
