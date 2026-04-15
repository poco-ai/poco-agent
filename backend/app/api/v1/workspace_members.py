import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_member import WorkspaceMemberResponse
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
