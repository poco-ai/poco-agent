import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.response import Response, ResponseSchema
from app.schemas.agent_assignment import (
    AgentAssignmentActionResponse,
    AgentAssignmentResponse,
)
from app.schemas.workspace_issue import (
    WorkspaceIssueCreateRequest,
    WorkspaceIssueMoveRequest,
    WorkspaceIssueResponse,
    WorkspaceIssueUpdateRequest,
)
from app.services.agent_assignment_service import AgentAssignmentService
from app.services.workspace_issue_service import WorkspaceIssueService

router = APIRouter(prefix="/workspace-boards/{board_id}/issues", tags=["workspace-issues"])
detail_router = APIRouter(prefix="/workspace-issues", tags=["workspace-issues"])

service = WorkspaceIssueService()
assignment_service = AgentAssignmentService()


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


@detail_router.get("/{issue_id}", response_model=ResponseSchema[WorkspaceIssueResponse])
async def get_workspace_issue(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_issue(db, current_user, issue_id)
    return Response.success(data=result, message="Workspace issue retrieved successfully")


@detail_router.post("/{issue_id}/move", response_model=ResponseSchema[WorkspaceIssueResponse])
async def move_workspace_issue(
    issue_id: uuid.UUID,
    request: WorkspaceIssueMoveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.move_issue(db, current_user, issue_id, request)
    return Response.success(data=result, message="Workspace issue moved successfully")


@detail_router.get(
    "/{issue_id}/agent-assignment",
    response_model=ResponseSchema[AgentAssignmentResponse | None],
)
async def get_issue_agent_assignment(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = assignment_service.get_assignment_for_issue(
        db,
        current_user=current_user,
        issue_id=issue_id,
    )
    return Response.success(data=result, message="Agent assignment retrieved successfully")


@detail_router.post(
    "/{issue_id}/agent-assignment/trigger",
    response_model=ResponseSchema[AgentAssignmentActionResponse],
)
async def trigger_issue_agent_assignment(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = assignment_service.trigger_assignment(
        db,
        current_user=current_user,
        issue_id=issue_id,
    )
    return Response.success(data=result, message="Agent assignment triggered successfully")


@detail_router.post(
    "/{issue_id}/agent-assignment/retry",
    response_model=ResponseSchema[AgentAssignmentActionResponse],
)
async def retry_issue_agent_assignment(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = assignment_service.retry_assignment(
        db,
        current_user=current_user,
        issue_id=issue_id,
    )
    return Response.success(data=result, message="Agent assignment retried successfully")


@detail_router.post(
    "/{issue_id}/agent-assignment/cancel",
    response_model=ResponseSchema[AgentAssignmentActionResponse],
)
async def cancel_issue_agent_assignment(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = assignment_service.cancel_assignment(
        db,
        current_user=current_user,
        issue_id=issue_id,
    )
    return Response.success(data=result, message="Agent assignment cancelled successfully")


@detail_router.post(
    "/{issue_id}/agent-assignment/release",
    response_model=ResponseSchema[AgentAssignmentActionResponse],
)
async def release_issue_agent_assignment(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = assignment_service.release_assignment_container(
        db,
        current_user=current_user,
        issue_id=issue_id,
    )
    return Response.success(data=result, message="Agent sandbox released successfully")
