from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.middleware.request_context import (
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    RequestContextMiddleware,
)
from app.core.middleware.request_logging import RequestLoggingMiddleware


def setup_middleware(app: FastAPI) -> None:
    # Inner -> outer: Starlette wraps last-added as the outermost.
    app.add_middleware(RequestLoggingMiddleware)

    # Keep CORS permissive by default; this service is typically called by IM platforms.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, TRACE_ID_HEADER],
    )

    app.add_middleware(RequestContextMiddleware)
