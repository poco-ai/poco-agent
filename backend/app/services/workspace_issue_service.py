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
    ISSUE_STATUS_VALUES,
    WorkspaceIssueCreateRequest,
    WorkspaceIssueMoveRequest,
    WorkspaceIssueResponse,
    WorkspaceIssueUpdateRequest,
)
from app.services.agent_assignment_service import AgentAssignmentService
from app.services.workspace_member_service import require_workspace_member


class WorkspaceIssueService:
    def __init__(self) -> None:
        self._assignment_service = AgentAssignmentService()

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in ISSUE_STATUS_VALUES:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Unsupported workspace issue status: {status}",
            )

    @staticmethod
    def _normalize_position(position: int, max_position: int) -> int:
        return max(0, min(position, max_position))

    @staticmethod
    def _resequence_column(issues: list[WorkspaceIssue], status: str) -> None:
        for index, issue in enumerate(issues):
            issue.status = status
            issue.position = index

    @staticmethod
    def _to_response(issue: WorkspaceIssue) -> WorkspaceIssueResponse:
        return WorkspaceIssueResponse.model_validate(issue)

    def _move_issue_within_board(
        self,
        db: Session,
        issue: WorkspaceIssue,
        *,
        target_status: str,
        target_position: int,
    ) -> None:
        self._validate_status(target_status)

        if issue.status == target_status:
            column_issues = WorkspaceIssueRepository.list_by_board_and_status(
                db,
                issue.board_id,
                target_status,
                exclude_issue_id=issue.id,
            )
            insert_at = self._normalize_position(target_position, len(column_issues))
            column_issues.insert(insert_at, issue)
            self._resequence_column(column_issues, target_status)
            return

        source_status = issue.status
        source_issues = WorkspaceIssueRepository.list_by_board_and_status(
            db,
            issue.board_id,
            source_status,
            exclude_issue_id=issue.id,
        )
        target_issues = WorkspaceIssueRepository.list_by_board_and_status(
            db,
            issue.board_id,
            target_status,
            exclude_issue_id=issue.id,
        )
        insert_at = self._normalize_position(target_position, len(target_issues))
        target_issues.insert(insert_at, issue)
        self._resequence_column(source_issues, source_status)
        self._resequence_column(target_issues, target_status)

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
        self._validate_status(request.status)

        sibling_issues = WorkspaceIssueRepository.list_by_board_and_status(
            db,
            board.id,
            request.status,
        )
        target_position = (
            len(sibling_issues)
            if request.position is None
            else self._normalize_position(request.position, len(sibling_issues))
        )

        issue = WorkspaceIssue(
            workspace_id=board.workspace_id,
            board_id=board.id,
            title=request.title.strip(),
            description=(request.description or "").strip() or None,
            status=request.status,
            position=target_position,
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
        sibling_issues.insert(target_position, issue)
        self._resequence_column(sibling_issues, request.status)
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
        status_was_updated = "status" in request.model_fields_set
        position_was_updated = "position" in request.model_fields_set
        for field, value in update.items():
            if field in {
                "trigger_mode",
                "schedule_cron",
                "assignment_prompt",
                "status",
                "position",
            }:
                continue
            setattr(issue, field, value)
        if status_was_updated or position_was_updated:
            target_status = request.status or issue.status
            if request.position is not None:
                target_position = request.position
            elif request.status is not None and request.status != issue.status:
                target_position = len(
                    WorkspaceIssueRepository.list_by_board_and_status(
                        db,
                        issue.board_id,
                        request.status,
                        exclude_issue_id=issue.id,
                    )
                )
            else:
                target_position = issue.position
            self._move_issue_within_board(
                db,
                issue,
                target_status=target_status,
                target_position=target_position,
            )
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

    def move_issue(
        self,
        db: Session,
        current_user: User,
        issue_id: uuid.UUID,
        request: WorkspaceIssueMoveRequest,
    ) -> WorkspaceIssueResponse:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)
        self._move_issue_within_board(
            db,
            issue,
            target_status=request.status,
            target_position=request.position,
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
