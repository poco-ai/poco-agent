import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.server_channel_message import (
    ServerChannelMessageCreateRequest,
    ServerChannelMessageContextResponse,
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionOperationResponse,
    ServerChannelMessageReactionRequest,
)
from app.services.server_channel_message_service import (
    ServerChannelMessageService,
)
from app.services.server_channel_message_reaction_service import (
    ServerChannelMessageReactionService,
)

router = APIRouter(
    prefix="/servers/{server_id}/channels/{channel_id}",
    tags=["server-channel-messages"],
)

service = ServerChannelMessageService()
reaction_service = ServerChannelMessageReactionService()


@router.get(
    "/messages", response_model=ResponseSchema[list[ServerChannelMessageResponse]]
)
async def list_channel_messages(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    before_message_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_messages(
        db,
        current_user,
        server_id,
        channel_id,
        before_message_id=before_message_id,
        limit=limit,
    )
    return Response.success(
        data=result,
        message="Server channel messages retrieved successfully",
    )


@router.post("/messages", response_model=ResponseSchema[ServerChannelMessageResponse])
async def send_channel_message(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    request: ServerChannelMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.send_message(db, current_user, server_id, channel_id, request)
    return Response.success(
        data=result,
        message="Server channel message sent successfully",
    )


@router.get(
    "/threads/{thread_root_message_id}",
    response_model=ResponseSchema[ServerChannelThreadResponse],
)
async def get_channel_thread(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    thread_root_message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_thread(
        db,
        current_user,
        server_id,
        channel_id,
        thread_root_message_id,
    )
    return Response.success(
        data=result,
        message="Server channel thread retrieved successfully",
    )


@router.get(
    "/messages/{message_id}/context",
    response_model=ResponseSchema[ServerChannelMessageContextResponse],
)
async def get_channel_message_context(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    message_id: uuid.UUID,
    before: int = Query(default=20, ge=0, le=100),
    after: int = Query(default=20, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_message_context(
        db,
        current_user,
        server_id,
        channel_id,
        message_id,
        before=before,
        after=after,
    )
    return Response.success(
        data=result,
        message="Server channel message context retrieved successfully",
    )


@router.post(
    "/messages/{message_id}/reactions",
    response_model=ResponseSchema[ServerChannelMessageReactionOperationResponse],
)
async def add_channel_message_reaction(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    message_id: uuid.UUID,
    request: ServerChannelMessageReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = reaction_service.add_user_reaction(
        db,
        current_user,
        server_id,
        channel_id,
        message_id,
        request.emoji,
    )
    return Response.success(
        data=result,
        message="Server channel message reaction added successfully",
    )


@router.delete(
    "/messages/{message_id}/reactions",
    response_model=ResponseSchema[ServerChannelMessageReactionOperationResponse],
)
async def remove_channel_message_reaction(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    message_id: uuid.UUID,
    request: ServerChannelMessageReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = reaction_service.remove_user_reaction(
        db,
        current_user,
        server_id,
        channel_id,
        message_id,
        request.emoji,
    )
    return Response.success(
        data=result,
        message="Server channel message reaction removed successfully",
    )
