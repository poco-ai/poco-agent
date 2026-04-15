import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace_issue import (
    WorkspaceIssueCreateRequest,
    WorkspaceIssueResponse,
    WorkspaceIssueUpdateRequest,
)
from app.services.workspace_issue_service import WorkspaceIssueService

router = APIRouter(prefix="/workspace-boards/{board_id}/issues", tags=["workspace-issues"])

service = WorkspaceIssueService()


@router.get("", response_model=ResponseSchema[list[WorkspaceIssueResponse]])
async def list_workspace_issues(
    board_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_issues(db, current_user, board_id)
    return Response.success(data=result, message="Workspace issues retrieved successfully")


@router.post("", response_model=ResponseSchema[WorkspaceIssueResponse])
async def create_workspace_issue(
    board_id: uuid.UUID,
    request: WorkspaceIssueCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_issue(db, current_user, board_id, request)
    return Response.success(data=result, message="Workspace issue created successfully")


@router.patch("/{issue_id}", response_model=ResponseSchema[WorkspaceIssueResponse])
async def update_workspace_issue(
    board_id: uuid.UUID,
    issue_id: uuid.UUID,
    request: WorkspaceIssueUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ = board_id
    result = service.update_issue(db, current_user, issue_id, request)
    return Response.success(data=result, message="Workspace issue updated successfully")


@router.delete("/{issue_id}", response_model=ResponseSchema[WorkspaceIssueResponse])
async def delete_workspace_issue(
    board_id: uuid.UUID,
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    _ = board_id
    result = service.delete_issue(db, current_user, issue_id)
    return Response.success(data=result, message="Workspace issue deleted successfully")
