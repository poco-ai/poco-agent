import uuid

from sqlalchemy.orm import Session

from app.core.audit import auditable
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.models.workspace_issue import WorkspaceIssue
from app.repositories.workspace_board_repository import WorkspaceBoardRepository
from app.repositories.workspace_issue_repository import WorkspaceIssueRepository
from app.schemas.workspace_issue import (
    WorkspaceIssueCreateRequest,
    WorkspaceIssueResponse,
    WorkspaceIssueUpdateRequest,
)
from app.services.agent_assignment_service import AgentAssignmentService
from app.services.workspace_member_service import require_workspace_member


class WorkspaceIssueService:
    def __init__(self) -> None:
        self._assignment_service = AgentAssignmentService()

    @staticmethod
    def _to_response(issue: WorkspaceIssue) -> WorkspaceIssueResponse:
        return WorkspaceIssueResponse.model_validate(issue)

    @auditable(
        action="issue.created",
        target_type="issue",
        target_id=lambda _args, result: result.issue_id,
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {"title": args["request"].title},
    )
    def create_issue(
        self,
        db: Session,
        current_user: User,
        board_id: uuid.UUID,
        request: WorkspaceIssueCreateRequest,
    ) -> WorkspaceIssueResponse:
        board = WorkspaceBoardRepository.get_by_id(db, board_id)
        if board is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace board not found: {board_id}",
            )
        require_workspace_member(db, board.workspace_id, current_user.id)

        issue = WorkspaceIssue(
            workspace_id=board.workspace_id,
            board_id=board.id,
            title=request.title.strip(),
            description=(request.description or "").strip() or None,
            status=request.status,
            type=request.type,
            priority=request.priority,
            due_date=request.due_date,
            assignee_user_id=request.assignee_user_id,
            assignee_preset_id=request.assignee_preset_id,
            reporter_user_id=request.reporter_user_id,
            related_project_id=request.related_project_id,
            creator_user_id=current_user.id,
            updated_by=current_user.id,
        )
        issue = WorkspaceIssueRepository.create(db, issue)
        db.flush()
        if request.assignee_preset_id is not None:
            self._assignment_service.sync_issue_assignment(
                db,
                current_user=current_user,
                issue=issue,
                preset_id=request.assignee_preset_id,
                trigger_mode=request.trigger_mode,
                schedule_cron=request.schedule_cron,
                prompt_override=request.assignment_prompt,
                auto_trigger=True,
            )
        db.commit()
        db.refresh(issue)
        return self._to_response(issue)

    def list_issues(
        self,
        db: Session,
        current_user: User,
        board_id: uuid.UUID,
    ) -> list[WorkspaceIssueResponse]:
        board = WorkspaceBoardRepository.get_by_id(db, board_id)
        if board is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace board not found: {board_id}",
            )
        require_workspace_member(db, board.workspace_id, current_user.id)
        return [
            self._to_response(issue)
            for issue in WorkspaceIssueRepository.list_by_board(db, board_id)
        ]

    def get_issue(
        self,
        db: Session,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> WorkspaceIssueResponse:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)
        return self._to_response(issue)

    @auditable(
        action="issue.updated",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: args["request"].model_dump(
            exclude_unset=True,
            mode="json",
        ),
    )
    @auditable(
        action="issue.status_changed",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {"status": args["request"].status},
        condition=lambda args, _result: "status" in args["request"].model_fields_set,
    )
    @auditable(
        action="issue.priority_changed",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {"priority": args["request"].priority},
        condition=lambda args, _result: "priority" in args["request"].model_fields_set,
    )
    @auditable(
        action="issue.assigned",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {
            "assignee_user_id": args["request"].assignee_user_id,
            "assignee_preset_id": args["request"].assignee_preset_id,
            "assignee_type": (
                "preset"
                if args["request"].assignee_preset_id is not None
                else "user"
            ),
        },
        condition=lambda args, _result: (
            (
                "assignee_user_id" in args["request"].model_fields_set
                or "assignee_preset_id" in args["request"].model_fields_set
            )
            and (
                args["request"].assignee_user_id is not None
                or args["request"].assignee_preset_id is not None
            )
        ),
    )
    @auditable(
        action="issue.unassigned",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        condition=lambda args, _result: (
            (
                "assignee_user_id" in args["request"].model_fields_set
                or "assignee_preset_id" in args["request"].model_fields_set
            )
            and args["request"].assignee_user_id is None
            and args["request"].assignee_preset_id is None
        ),
    )
    def update_issue(
        self,
        db: Session,
        current_user: User,
        issue_id: uuid.UUID,
        request: WorkspaceIssueUpdateRequest,
    ) -> WorkspaceIssueResponse:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)

        update = request.model_dump(exclude_unset=True)
        for field, value in update.items():
            if field in {"trigger_mode", "schedule_cron", "assignment_prompt"}:
                continue
            setattr(issue, field, value)
        if request.assignee_preset_id is not None:
            issue.assignee_user_id = None
        if (
            "assignee_preset_id" in request.model_fields_set
            or "assignee_user_id" in request.model_fields_set
            or "trigger_mode" in request.model_fields_set
            or "schedule_cron" in request.model_fields_set
            or "assignment_prompt" in request.model_fields_set
        ):
            self._assignment_service.sync_issue_assignment(
                db,
                current_user=current_user,
                issue=issue,
                preset_id=issue.assignee_preset_id,
                trigger_mode=request.trigger_mode,
                schedule_cron=request.schedule_cron,
                prompt_override=request.assignment_prompt,
                auto_trigger=issue.assignee_preset_id is not None
                and request.trigger_mode == "persistent_sandbox",
            )
        issue.updated_by = current_user.id
        db.commit()
        db.refresh(issue)
        return self._to_response(issue)

    @auditable(
        action="issue.deleted",
        target_type="issue",
        target_id=lambda args, _result: args["issue_id"],
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda _args, result: {"title": result.title},
    )
    def delete_issue(
        self,
        db: Session,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> WorkspaceIssueResponse:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)
        response = self._to_response(issue)
        db.delete(issue)
        db.commit()
        return response
