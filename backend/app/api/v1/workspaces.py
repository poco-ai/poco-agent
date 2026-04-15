import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_tenancy import (
    WorkspaceCreateRequest,
    WorkspaceOwnershipTransferRequest,
    WorkspaceResponse,
)
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


@router.post(
    "/{workspace_id}/ownership-transfer",
    response_model=ResponseSchema[WorkspaceResponse],
)
async def transfer_workspace_ownership(
    workspace_id: uuid.UUID,
    request: WorkspaceOwnershipTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.transfer_ownership(db, current_user, workspace_id, request)
    return Response.success(
        data=result,
        message="Workspace ownership transferred successfully",
    )


@router.delete("/{workspace_id}", response_model=ResponseSchema[dict])
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_workspace(db, current_user, workspace_id)
    return Response.success(
        data={"id": workspace_id},
        message="Workspace deleted successfully",
    )
