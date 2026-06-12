from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_callback_token
from app.schemas.response import Response, ResponseSchema
from app.services.backend_client import BackendClient

router = APIRouter(
    prefix="/agent-channel-runtime",
    tags=["agent-channel-runtime"],
    dependencies=[Depends(require_callback_token)],
)
backend_client = BackendClient()


def _split_session_payload(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    session_id = str(request.get("session_id") or "").strip()
    payload = {key: value for key, value in request.items() if key != "session_id"}
    return session_id, payload


@router.post("/messages/read", response_model=ResponseSchema[Any])
async def read_agent_channel_messages(
    request: dict[str, Any],
) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.read_agent_channel_messages(session_id, payload)
    return Response.success(data=result, message="Agent channel messages read")


@router.post("/agents/list", response_model=ResponseSchema[Any])
async def list_agent_channel_agents(
    request: dict[str, Any],
) -> JSONResponse:
    session_id, _ = _split_session_payload(request)
    result = await backend_client.list_agent_channel_agents(session_id)
    return Response.success(data=result, message="Agent channel agents listed")


@router.post("/collaboration/request", response_model=ResponseSchema[Any])
async def request_agent_channel_collaboration(
    request: dict[str, Any],
) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.request_agent_channel_collaboration(
        session_id,
        payload,
    )
    return Response.success(data=result, message="Agent collaboration requested")


@router.post("/reactions/add", response_model=ResponseSchema[Any])
async def add_agent_channel_message_reaction(
    request: dict[str, Any],
) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.add_agent_channel_message_reaction(
        session_id,
        payload,
    )
    return Response.success(data=result, message="Agent channel reaction added")


@router.post("/reactions/remove", response_model=ResponseSchema[Any])
async def remove_agent_channel_message_reaction(
    request: dict[str, Any],
) -> JSONResponse:
    session_id, payload = _split_session_payload(request)
    result = await backend_client.remove_agent_channel_message_reaction(
        session_id,
        payload,
    )
    return Response.success(data=result, message="Agent channel reaction removed")
