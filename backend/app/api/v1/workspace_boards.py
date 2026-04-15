import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_board import (
    WorkspaceBoardCreateRequest,
    WorkspaceBoardResponse,
)
from app.services.workspace_board_service import WorkspaceBoardService

router = APIRouter(prefix="/workspaces/{workspace_id}/boards", tags=["workspace-boards"])

service = WorkspaceBoardService()


@router.get("", response_model=ResponseSchema[list[WorkspaceBoardResponse]])
async def list_workspace_boards(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_boards(db, current_user, workspace_id)
    return Response.success(data=result, message="Workspace boards retrieved successfully")


@router.post("", response_model=ResponseSchema[WorkspaceBoardResponse])
async def create_workspace_board(
    workspace_id: uuid.UUID,
    request: WorkspaceBoardCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_board(db, current_user, workspace_id, request)
    return Response.success(data=result, message="Workspace board created successfully")


@router.patch("/{board_id}", response_model=ResponseSchema[WorkspaceBoardResponse])
async def update_workspace_board(
    workspace_id: uuid.UUID,
    board_id: uuid.UUID,
    request: WorkspaceBoardCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ = workspace_id
    result = service.update_board(db, current_user, board_id, request)
    return Response.success(data=result, message="Workspace board updated successfully")


@router.delete("/{board_id}", response_model=ResponseSchema[WorkspaceBoardResponse])
async def delete_workspace_board(
    workspace_id: uuid.UUID,
    board_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ = workspace_id
    result = service.delete_board(db, current_user, board_id)
    return Response.success(data=result, message="Workspace board deleted successfully")
