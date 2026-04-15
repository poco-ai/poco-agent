import uuid
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.activity_log import ActivityLog
from app.models.agent_assignment import AgentAssignment
from app.models.user import User
from app.models.workspace_issue import WorkspaceIssue
from app.repositories.activity_log_repository import ActivityLogRepository
from app.repositories.agent_assignment_repository import AgentAssignmentRepository
from app.repositories.preset_repository import PresetRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_queue_item_repository import SessionQueueItemRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.workspace_issue_repository import WorkspaceIssueRepository
from app.schemas.agent_assignment import (
    AgentAssignmentActionResponse,
    AgentAssignmentDispatchResponse,
    AgentAssignmentResponse,
)
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest
from app.services.executor_manager_client import ExecutorManagerClient
from app.services.prompt_builder import PromptBuilder
from app.services.session_service import SessionService
from app.services.task_service import TaskService
from app.services.workspace_member_service import require_workspace_member


class AgentAssignmentService:
    def __init__(
        self,
        *,
        task_service: TaskService | None = None,
        session_service: SessionService | None = None,
        prompt_builder: PromptBuilder | None = None,
        executor_manager_client: ExecutorManagerClient | None = None,
    ) -> None:
        self._task_service = task_service or TaskService()
        self._session_service = session_service or SessionService()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._executor_manager_client = executor_manager_client or ExecutorManagerClient()
        self._audit_rules = get_settings().audit_rules

    @staticmethod
    def _to_response(assignment: AgentAssignment) -> AgentAssignmentResponse:
        return AgentAssignmentResponse.model_validate(assignment)

    def _log_activity(
        self,
        db: Session,
        *,
        action: str,
        actor_user_id: str,
        assignment: AgentAssignment,
        metadata: dict | None = None,
    ) -> None:
        if self._audit_rules.get(action, self._audit_rules.get("default", True)) is False:
            return
        ActivityLogRepository.create(
            db,
            ActivityLog(
                workspace_id=assignment.workspace_id,
                actor_user_id=actor_user_id,
                action=action,
                target_type="agent_assignment",
                target_id=str(assignment.id),
                metadata_json=metadata or {},
            ),
        )

    @staticmethod
    def _validate_cron(expr: str | None) -> str:
        value = (expr or "").strip()
        if not value:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="schedule_cron cannot be empty for scheduled assignments",
            )
        if not croniter.is_valid(value):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid cron expression: {value}",
            )
        return value

    @staticmethod
    def _build_container_id(session_id: uuid.UUID) -> str:
        return f"exec-{str(session_id)[:8]}"

    def _resolve_preset_for_user(self, db: Session, user_id: str, preset_id: int):
        preset = PresetRepository.get_visible_by_id(db, preset_id, user_id)
        if preset is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Preset not found: {preset_id}",
            )
        return preset

    def _build_prompt(
        self,
        db: Session,
        issue: WorkspaceIssue,
        prompt_override: str | None,
    ) -> str:
        prompt = (prompt_override or "").strip()
        if prompt:
            return prompt
        built = self._prompt_builder.build_issue_prompt(db, issue).strip()
        if not built:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Unable to build a prompt from the issue",
            )
        return built

    def _get_session(self, db: Session, assignment: AgentAssignment):
        if assignment.session_id is None:
            return None
        return SessionRepository.get_by_id_for_update(db, assignment.session_id)

    def _has_active_execution(self, db: Session, assignment: AgentAssignment) -> bool:
        if assignment.session_id is None:
            return False
        if SessionQueueItemRepository.has_active_items(db, assignment.session_id):
            return True
        return RunRepository.get_blocking_by_session(db, assignment.session_id) is not None

    def _resolve_container_mode(self, db: Session, assignment: AgentAssignment) -> str:
        if assignment.trigger_mode == "persistent_sandbox":
            return "persistent"
        preset = self._resolve_preset_for_user(db, assignment.created_by, assignment.preset_id)
        return preset.container_mode or "ephemeral"

    def _require_issue_for_user(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> WorkspaceIssue:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)
        return issue

    def _enqueue_run(
        self,
        db: Session,
        *,
        actor_user_id: str,
        assignment: AgentAssignment,
        issue: WorkspaceIssue,
        audit_action: str,
    ) -> AgentAssignmentActionResponse:
        if self._has_active_execution(db, assignment):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Agent assignment already has an active execution",
            )

        container_mode = self._resolve_container_mode(db, assignment)
        task_request = TaskEnqueueRequest(
            prompt=assignment.prompt,
            session_id=assignment.session_id,
            project_id=issue.related_project_id,
            permission_mode="acceptEdits",
            schedule_mode="immediate",
            config=TaskConfig(
                preset_id=assignment.preset_id,
                container_mode=container_mode,
                filesystem_mode="sandbox",
            ),
        )
        result = self._task_service.enqueue_task(db, actor_user_id, task_request)

        assignment.session_id = result.session_id
        assignment.status = "pending"
        assignment.last_triggered_at = datetime.now(timezone.utc)
        assignment.last_completed_at = None
        assignment.container_id = (
            self._build_container_id(result.session_id)
            if container_mode == "persistent"
            else None
        )
        issue.status = "in_progress"
        db.flush()

        self._log_activity(
            db,
            action=audit_action,
            actor_user_id=actor_user_id,
            assignment=assignment,
            metadata={
                "issue_id": str(issue.id),
                "preset_id": assignment.preset_id,
                "trigger_mode": assignment.trigger_mode,
                "session_id": str(assignment.session_id) if assignment.session_id else None,
            },
        )
        db.commit()
        db.refresh(assignment)
        db.refresh(issue)
        return AgentAssignmentActionResponse(
            assignment=self._to_response(assignment),
            issue_status=issue.status,
        )

    def _cancel_existing_session(
        self,
        db: Session,
        *,
        actor_user_id: str,
        assignment: AgentAssignment,
    ) -> None:
        if assignment.session_id is None:
            return
        session = SessionRepository.get_by_id(db, assignment.session_id)
        if session is None:
            return
        if session.status not in {"pending", "running", "canceling"}:
            return
        self._session_service.cancel_session(
            db,
            assignment.session_id,
            user_id=actor_user_id,
            reason="Agent assignment canceled",
        )

    def sync_issue_assignment(
        self,
        db: Session,
        *,
        current_user: User,
        issue: WorkspaceIssue,
        preset_id: int | None,
        trigger_mode: str | None,
        schedule_cron: str | None,
        prompt_override: str | None,
        auto_trigger: bool,
    ) -> AgentAssignment | None:
        existing = AgentAssignmentRepository.get_by_issue_id(db, issue.id)

        if preset_id is None:
            if existing is None:
                return None
            self._cancel_existing_session(
                db,
                actor_user_id=current_user.id,
                assignment=existing,
            )
            existing.status = "cancelled"
            existing.container_id = None
            existing.prompt = self._build_prompt(db, issue, prompt_override or existing.prompt)
            issue.assignee_preset_id = None
            if issue.status != "done":
                issue.status = "todo"
            self._log_activity(
                db,
                action="agent_assignment.cancelled",
                actor_user_id=current_user.id,
                assignment=existing,
                metadata={"issue_id": str(issue.id), "preset_id": existing.preset_id},
            )
            return existing

        preset = self._resolve_preset_for_user(db, current_user.id, preset_id)
        mode = trigger_mode or (existing.trigger_mode if existing is not None else None)
        if mode not in {"persistent_sandbox", "scheduled_task"}:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="trigger_mode is required when assigning an AI preset",
            )

        prompt = self._build_prompt(db, issue, prompt_override)
        cron_value = (
            self._validate_cron(schedule_cron)
            if mode == "scheduled_task"
            else None
        )

        created = existing is None
        assignment = existing or AgentAssignment(
            workspace_id=issue.workspace_id,
            issue_id=issue.id,
            preset_id=preset.id,
            trigger_mode=mode,
            prompt=prompt,
            created_by=current_user.id,
            status="pending",
        )
        assignment.preset_id = preset.id
        assignment.trigger_mode = mode
        assignment.prompt = prompt
        assignment.schedule_cron = cron_value
        if created:
            AgentAssignmentRepository.create(db, assignment)
        else:
            assignment.status = "pending"
            if existing.preset_id != preset.id or existing.trigger_mode != mode:
                assignment.session_id = None
                assignment.container_id = None
                assignment.last_triggered_at = None
                assignment.last_completed_at = None

        issue.assignee_user_id = None
        issue.assignee_preset_id = preset.id
        if mode == "scheduled_task":
            issue.status = issue.status if issue.status == "done" else "todo"
        else:
            issue.status = "in_progress"

        if created:
            self._log_activity(
                db,
                action="agent_assignment.created",
                actor_user_id=current_user.id,
                assignment=assignment,
                metadata={
                    "issue_id": str(issue.id),
                    "preset_id": assignment.preset_id,
                    "trigger_mode": assignment.trigger_mode,
                },
            )

        if auto_trigger and mode == "persistent_sandbox":
            db.flush()
            self._enqueue_run(
                db,
                actor_user_id=current_user.id,
                assignment=assignment,
                issue=issue,
                audit_action="agent_assignment.triggered",
            )

        return assignment

    def get_assignment_for_issue(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> AgentAssignmentResponse | None:
        issue = WorkspaceIssueRepository.get_by_id(db, issue_id)
        if issue is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        if issue.workspace_id is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace issue not found: {issue_id}",
            )
        require_workspace_member(db, issue.workspace_id, current_user.id)
        assignment = AgentAssignmentRepository.get_by_issue_id(db, issue_id)
        return self._to_response(assignment) if assignment is not None else None

    def trigger_assignment(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> AgentAssignmentActionResponse:
        issue = self._require_issue_for_user(
            db,
            current_user=current_user,
            issue_id=issue_id,
        )
        assignment = AgentAssignmentRepository.get_by_issue_id(db, issue_id)
        if assignment is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent assignment not found for issue",
            )
        return self._enqueue_run(
            db,
            actor_user_id=current_user.id,
            assignment=assignment,
            issue=issue,
            audit_action="agent_assignment.triggered",
        )

    def retry_assignment(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> AgentAssignmentActionResponse:
        issue = self._require_issue_for_user(
            db,
            current_user=current_user,
            issue_id=issue_id,
        )
        assignment = AgentAssignmentRepository.get_by_issue_id(db, issue_id)
        if assignment is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent assignment not found for issue",
            )
        assignment.status = "pending"
        return self._enqueue_run(
            db,
            actor_user_id=current_user.id,
            assignment=assignment,
            issue=issue,
            audit_action="agent_assignment.retried",
        )

    def cancel_assignment(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> AgentAssignmentActionResponse:
        issue = self._require_issue_for_user(
            db,
            current_user=current_user,
            issue_id=issue_id,
        )
        assignment = AgentAssignmentRepository.get_by_issue_id(db, issue_id)
        if assignment is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent assignment not found for issue",
            )
        self._cancel_existing_session(
            db,
            actor_user_id=current_user.id,
            assignment=assignment,
        )
        assignment.status = "cancelled"
        assignment.container_id = None
        issue.status = "todo"
        issue.assignee_preset_id = None
        self._log_activity(
            db,
            action="agent_assignment.cancelled",
            actor_user_id=current_user.id,
            assignment=assignment,
            metadata={"issue_id": str(issue.id), "preset_id": assignment.preset_id},
        )
        db.commit()
        db.refresh(assignment)
        db.refresh(issue)
        return AgentAssignmentActionResponse(
            assignment=self._to_response(assignment),
            issue_status=issue.status,
        )

    def release_assignment_container(
        self,
        db: Session,
        *,
        current_user: User,
        issue_id: uuid.UUID,
    ) -> AgentAssignmentActionResponse:
        issue = self._require_issue_for_user(
            db,
            current_user=current_user,
            issue_id=issue_id,
        )
        assignment = AgentAssignmentRepository.get_by_issue_id(db, issue_id)
        if assignment is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent assignment not found for issue",
            )
        if not assignment.container_id:
            return AgentAssignmentActionResponse(
                assignment=self._to_response(assignment),
                issue_status=issue.status,
            )
        try:
            self._executor_manager_client.delete_container(assignment.container_id)
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=f"Failed to release sandbox container: {exc}",
            ) from exc
        assignment.container_id = None
        self._log_activity(
            db,
            action="agent_assignment.released",
            actor_user_id=current_user.id,
            assignment=assignment,
            metadata={"issue_id": str(issue.id)},
        )
        db.commit()
        db.refresh(assignment)
        return AgentAssignmentActionResponse(
            assignment=self._to_response(assignment),
            issue_status=issue.status,
        )

    def sync_callback_status(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        callback_status: str,
        error_message: str | None = None,
    ) -> None:
        assignment = AgentAssignmentRepository.get_by_session_id(db, session_id)
        if assignment is None:
            return
        issue = WorkspaceIssueRepository.get_by_id(db, assignment.issue_id)
        if issue is None:
            return

        if callback_status == "running":
            assignment.status = "running"
            issue.status = "in_progress"
            return

        if callback_status == "completed":
            assignment.status = "completed"
            assignment.last_completed_at = datetime.now(timezone.utc)
            issue.status = "done"
            self._log_activity(
                db,
                action="agent_assignment.completed",
                actor_user_id=assignment.created_by,
                assignment=assignment,
                metadata={"issue_id": str(issue.id), "session_id": str(session_id)},
            )
            return

        if callback_status == "failed":
            assignment.status = "failed"
            issue.status = "in_progress"
            self._log_activity(
                db,
                action="agent_assignment.failed",
                actor_user_id=assignment.created_by,
                assignment=assignment,
                metadata={
                    "issue_id": str(issue.id),
                    "session_id": str(session_id),
                    "error_message": error_message,
                },
            )

    def dispatch_due(
        self,
        db: Session,
        *,
        limit: int,
    ) -> AgentAssignmentDispatchResponse:
        now_utc = datetime.now(timezone.utc)
        assignments = AgentAssignmentRepository.list_schedulable(db, limit=limit)
        dispatched_ids: list[uuid.UUID] = []
        skipped = 0
        errors = 0

        for assignment in assignments:
            try:
                issue = WorkspaceIssueRepository.get_by_id(db, assignment.issue_id)
                if issue is None:
                    errors += 1
                    continue
                if assignment.last_triggered_at is not None:
                    itr = croniter(assignment.schedule_cron, assignment.last_triggered_at)
                    next_run_at = itr.get_next(datetime)
                    if next_run_at.tzinfo is None:
                        next_run_at = next_run_at.replace(tzinfo=timezone.utc)
                    if next_run_at.astimezone(timezone.utc) > now_utc:
                        skipped += 1
                        continue

                if self._has_active_execution(db, assignment):
                    assignment.last_triggered_at = now_utc
                    skipped += 1
                    continue

                response = self._enqueue_run(
                    db,
                    actor_user_id=assignment.created_by,
                    assignment=assignment,
                    issue=issue,
                    audit_action="agent_assignment.triggered",
                )
                dispatched_ids.append(response.assignment.assignment_id)
            except Exception:
                errors += 1

        return AgentAssignmentDispatchResponse(
            dispatched=len(dispatched_ids),
            assignment_ids=dispatched_ids,
            skipped=skipped,
            errors=errors,
        )
