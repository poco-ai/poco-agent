from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_tenancy import WorkspaceCreateRequest, WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

service = WorkspaceService()


@router.get("", response_model=ResponseSchema[list[WorkspaceResponse]])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_workspaces(db, current_user)
    return Response.success(data=result, message="Workspaces retrieved successfully")


@router.post("", response_model=ResponseSchema[WorkspaceResponse])
async def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_workspace(db, current_user, request)
    return Response.success(data=result, message="Workspace created successfully")
