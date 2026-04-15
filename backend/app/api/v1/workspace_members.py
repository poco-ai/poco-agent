import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_member import (
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdateRequest,
)
from app.services.workspace_member_service import WorkspaceMemberService

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["workspace-members"])

service = WorkspaceMemberService()


@router.get("", response_model=ResponseSchema[list[WorkspaceMemberResponse]])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_members(db, current_user, workspace_id)
    return Response.success(
        data=result,
        message="Workspace members retrieved successfully",
    )


@router.patch(
    "/{membership_id}/role",
    response_model=ResponseSchema[WorkspaceMemberResponse],
)
async def update_workspace_member_role(
    workspace_id: uuid.UUID,
    membership_id: int,
    request: WorkspaceMemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_member_role(
        db,
        current_user,
        workspace_id,
        membership_id,
        request,
    )
    return Response.success(
        data=result,
        message="Workspace member role updated successfully",
    )
