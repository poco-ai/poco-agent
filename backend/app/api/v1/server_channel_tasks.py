import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.server_channel_task import (
    ServerChannelTaskCandidateResponse,
    ServerChannelTaskClaimRequest,
    ServerChannelTaskCreateRequest,
    ServerChannelTaskResponse,
    ServerChannelTaskStatusUpdateRequest,
    ServerChannelTaskUpdateRequest,
)
from app.services.server_channel_task_service import ServerChannelTaskService

router = APIRouter(
    prefix="/servers/{server_id}/channels/{channel_id}/tasks",
    tags=["server-channel-tasks"],
)

service = ServerChannelTaskService()


@router.get("", response_model=ResponseSchema[list[ServerChannelTaskResponse]])
async def list_server_channel_tasks(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_tasks(db, current_user, server_id, channel_id)
    return Response.success(
        data=result, message="Server channel tasks retrieved successfully"
    )


@router.post("", response_model=ResponseSchema[ServerChannelTaskResponse])
async def create_server_channel_task(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    request: ServerChannelTaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_task(db, current_user, server_id, channel_id, request)
    return Response.success(
        data=result, message="Server channel task created successfully"
    )


@router.get(
    "/candidates",
    response_model=ResponseSchema[list[ServerChannelTaskCandidateResponse]],
)
async def list_server_channel_task_candidates(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    q: str | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_task_candidates(
        db,
        current_user,
        server_id,
        channel_id,
        query=q,
        limit=limit,
    )
    return Response.success(
        data=result,
        message="Server channel task candidates retrieved successfully",
    )


@router.get("/{task_id}", response_model=ResponseSchema[ServerChannelTaskResponse])
async def get_server_channel_task(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_task(db, current_user, server_id, channel_id, task_id)
    return Response.success(
        data=result, message="Server channel task retrieved successfully"
    )


@router.patch("/{task_id}", response_model=ResponseSchema[ServerChannelTaskResponse])
async def update_server_channel_task(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    task_id: uuid.UUID,
    request: ServerChannelTaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_task(
        db, current_user, server_id, channel_id, task_id, request
    )
    return Response.success(
        data=result, message="Server channel task updated successfully"
    )


@router.post(
    "/{task_id}/status", response_model=ResponseSchema[ServerChannelTaskResponse]
)
async def update_server_channel_task_status(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    task_id: uuid.UUID,
    request: ServerChannelTaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_task_status(
        db,
        current_user,
        server_id,
        channel_id,
        task_id,
        request,
    )
    return Response.success(
        data=result,
        message="Server channel task status updated successfully",
    )


@router.post(
    "/{task_id}/claim", response_model=ResponseSchema[ServerChannelTaskResponse]
)
async def claim_server_channel_task(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    task_id: uuid.UUID,
    request: ServerChannelTaskClaimRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.claim_task(
        db, current_user, server_id, channel_id, task_id, request
    )
    return Response.success(
        data=result, message="Server channel task claimed successfully"
    )


@router.post(
    "/{task_id}/unclaim", response_model=ResponseSchema[ServerChannelTaskResponse]
)
async def unclaim_server_channel_task(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.unclaim_task(db, current_user, server_id, channel_id, task_id)
    return Response.success(
        data=result, message="Server channel task unclaimed successfully"
    )
