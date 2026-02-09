import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.errors.exceptions import AppException
from app.schemas.response import Response

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI, *, debug: bool) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return Response.error(
            code=exc.code,
            message=exc.message,
            data=exc.details,
            status_code=400,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        return Response.error(
            code=exc.status_code,
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        if debug:
            return Response.error(
                code=500,
                message=str(exc),
                status_code=500,
            )
        return Response.error(
            code=500, message="Internal server error", status_code=500
        )
