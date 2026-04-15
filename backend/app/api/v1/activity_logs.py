import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.activity_log import ActivityLogResponse
from app.schemas.response import Response, ResponseSchema
from app.services.activity_logger import ActivityLogger
from app.services.workspace_member_service import require_workspace_member

router = APIRouter(prefix="/workspaces/{workspace_id}/activity", tags=["activity"])

service = ActivityLogger()


@router.get("", response_model=ResponseSchema[list[ActivityLogResponse]])
async def list_workspace_activity(
    workspace_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    require_workspace_member(db, workspace_id, current_user.id)
    result = service.list_workspace_activity(db, workspace_id, limit=limit)
    return Response.success(
        data=result,
        message="Workspace activity retrieved successfully",
    )
