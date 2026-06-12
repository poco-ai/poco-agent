from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_callback_token
from app.schemas.response import Response, ResponseSchema
from app.services.backend_client import BackendClient

router = APIRouter(
    prefix="/agent-channel-tasks",
    tags=["agent-channel-tasks"],
    dependencies=[Depends(require_callback_token)],
)
backend_client = BackendClient()


def _split_session_payload(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    return session_id, payload


@router.post("/list", response_model=ResponseSchema[Any])
async def list_agent_channel_tasks(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.list_agent_channel_tasks(session_id, payload)
    return Response.success(data=result, message="Agent channel tasks listed")


@router.post("/read", response_model=ResponseSchema[Any])
async def read_agent_channel_task(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.read_agent_channel_task(session_id, payload)
    return Response.success(data=result, message="Agent channel task read")


@router.post("/create", response_model=ResponseSchema[Any])
async def create_agent_channel_task(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.create_agent_channel_task(session_id, payload)
    return Response.success(data=result, message="Agent channel task created")


@router.post("/status", response_model=ResponseSchema[Any])
async def update_agent_channel_task_status(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.update_agent_channel_task_status(session_id, payload)
    return Response.success(data=result, message="Agent channel task status updated")


@router.post("/claim", response_model=ResponseSchema[Any])
async def claim_agent_channel_task(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.claim_agent_channel_task(session_id, payload)
    return Response.success(data=result, message="Agent channel task claimed")


@router.post("/comment", response_model=ResponseSchema[Any])
async def comment_agent_channel_task(request: dict[str, Any]) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.comment_agent_channel_task(session_id, payload)
    return Response.success(data=result, message="Agent channel task commented")
