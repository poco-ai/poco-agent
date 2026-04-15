import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_invite import (
    WorkspaceInviteAcceptRequest,
    WorkspaceInviteCreateRequest,
    WorkspaceInviteResponse,
)
from app.schemas.workspace_member import WorkspaceMemberResponse
from app.services.workspace_invite_service import WorkspaceInviteService

router = APIRouter(prefix="/workspaces/{workspace_id}/invites", tags=["workspace-invites"])
accept_router = APIRouter(prefix="/workspace-invites", tags=["workspace-invites"])

service = WorkspaceInviteService()


@router.get("", response_model=ResponseSchema[list[WorkspaceInviteResponse]])
async def list_workspace_invites(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_invites(db, current_user, workspace_id)
    return Response.success(
        data=result,
        message="Workspace invites retrieved successfully",
    )


@router.post("", response_model=ResponseSchema[WorkspaceInviteResponse])
async def create_workspace_invite(
    workspace_id: uuid.UUID,
    request: WorkspaceInviteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_invite(db, current_user, workspace_id, request)
    return Response.success(data=result, message="Workspace invite created successfully")


@accept_router.post("/accept", response_model=ResponseSchema[WorkspaceMemberResponse])
async def accept_workspace_invite(
    request: WorkspaceInviteAcceptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.accept_invite(db, current_user, request)
    return Response.success(
        data=result,
        message="Workspace invite accepted successfully",
    )
