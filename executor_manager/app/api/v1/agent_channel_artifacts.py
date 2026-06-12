from typing import Any

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response as FastAPIResponse

from app.core.deps import require_callback_token
from app.schemas.response import Response, ResponseSchema
from app.services.backend_client import BackendClient

router = APIRouter(
    prefix="/agent-channel-artifacts",
    tags=["agent-channel-artifacts"],
    dependencies=[Depends(require_callback_token)],
)
backend_client = BackendClient()


def _upstream_error_response(exc: httpx.HTTPStatusError) -> JSONResponse:
    response = exc.response
    try:
        body = response.json()
    except ValueError:
        return Response.error(
            code=response.status_code,
            message=response.text or response.reason_phrase,
            status_code=response.status_code,
        )
    if isinstance(body, dict):
        return JSONResponse(status_code=response.status_code, content=body)
    return Response.error(
        code=response.status_code,
        message=response.reason_phrase,
        data=body,
        status_code=response.status_code,
    )


@router.post("/list", response_model=ResponseSchema[Any])
async def list_agent_channel_artifacts(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    try:
        result = await backend_client.list_agent_channel_artifacts(session_id)
    except httpx.HTTPStatusError as exc:
        return _upstream_error_response(exc)
    return Response.success(data=result, message="Agent channel artifacts listed")


@router.post("/read", response_model=ResponseSchema[Any])
async def read_agent_channel_artifact(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    try:
        result = await backend_client.read_agent_channel_artifact(session_id, payload)
    except httpx.HTTPStatusError as exc:
        return _upstream_error_response(exc)
    return Response.success(data=result, message="Agent channel artifact read")


@router.post("/search", response_model=ResponseSchema[Any])
async def search_agent_channel_artifacts(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    try:
        result = await backend_client.search_agent_channel_artifacts(
            session_id, payload
        )
    except httpx.HTTPStatusError as exc:
        return _upstream_error_response(exc)
    return Response.success(data=result, message="Agent channel artifacts searched")


@router.post("/text", response_model=ResponseSchema[Any])
async def read_agent_channel_artifact_text(request: dict[str, Any]) -> JSONResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    try:
        result = await backend_client.read_agent_channel_artifact_text(
            session_id, payload
        )
    except httpx.HTTPStatusError as exc:
        return _upstream_error_response(exc)
    return Response.success(data=result, message="Agent channel artifact text read")


@router.post("/download")
async def download_agent_channel_artifact(request: dict[str, Any]) -> FastAPIResponse:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    try:
        result = await backend_client.download_agent_channel_artifact(
            session_id, payload
        )
    except httpx.HTTPStatusError as exc:
        return _upstream_error_response(exc)
    return FastAPIResponse(
        content=result.content,
        media_type=result.media_type,
        headers=result.headers,
    )
