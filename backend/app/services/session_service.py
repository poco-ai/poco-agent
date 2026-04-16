import logging
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, TypeVar

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.models.agent_run import AgentRun
from app.models.usage_log import UsageLog
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.repositories.session_queue_item_repository import SessionQueueItemRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.repositories.user_input_request_repository import UserInputRequestRepository
from app.schemas.internal_session import (
    SessionCancellationClaimResponse,
    SessionCancellationCompleteResponse,
)
from app.schemas.session import (
    SessionCancelResponse,
    SessionCreateRequest,
    SessionUpdateRequest,
)
from app.schemas.task import TaskEnqueueResponse
from app.services.session_queue_service import SessionQueueService
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)
JsonValueT = TypeVar("JsonValueT")
task_service = TaskService()


class SessionService:
    """Service layer for session management."""

    ACTIVE_CANCELLATION_RUN_STATUSES = {"claimed", "running", "canceling"}
    QUEUED_RUN_STATUSES = {"queued"}

    @staticmethod
    def _deepcopy_json(value: JsonValueT) -> JsonValueT:
        if isinstance(value, dict | list):
            return deepcopy(value)
        return value

    def _ensure_no_active_queue_items(self, db: Session, session_id: uuid.UUID) -> None:
        if SessionQueueItemRepository.has_active_items(db, session_id):
            raise AppException(
                error_code=ErrorCode.SESSION_HAS_ACTIVE_QUEUE_ITEMS,
                message="Queued queries must be cleared before modifying this session",
            )

    @staticmethod
    def _ensure_session_not_canceling(db_session: AgentSession) -> None:
        if db_session.status == "canceling":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session cancellation is still in progress",
            )

    @staticmethod
    def _has_pending_cancellation(db_session: AgentSession) -> bool:
        return (
            db_session.status == "canceling"
            and db_session.cancellation_requested_at is not None
            and db_session.cancellation_completed_at is None
        )

    @staticmethod
    def _mark_tool_executions_canceled(
        *,
        executions: list[Any],
        now: datetime,
        reason: str | None,
    ) -> None:
        if not executions:
            return

        suffix = (
            f": {reason.strip()}" if isinstance(reason, str) and reason.strip() else ""
        )
        for execution in executions:
            execution.is_error = True
            execution.tool_output = {"content": f"Canceled{suffix}"}
            if execution.duration_ms is None and execution.created_at is not None:
                started_at = execution.created_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                duration = now - started_at.astimezone(timezone.utc)
                execution.duration_ms = max(0, int(duration.total_seconds() * 1000))

    @staticmethod
    def _sync_scheduled_task_canceled(db: Session, run: AgentRun) -> None:
        if not run.scheduled_task_id:
            return

        db_task = ScheduledTaskRepository.get_by_id(db, run.scheduled_task_id)
        if db_task and (not db_task.last_run_id or db_task.last_run_id == run.id):
            db_task.last_run_id = run.id
            db_task.last_run_status = "canceled"
            db_task.last_error = None

    def _mark_run_canceled(
        self,
        db: Session,
        run: AgentRun,
        *,
        now: datetime,
        clear_claim: bool,
    ) -> bool:
        if run.status == "canceled":
            return False

        run.status = "canceled"
        if run.finished_at is None:
            run.finished_at = now
        if clear_claim:
            run.claimed_by = None
            run.lease_expires_at = None
        self._sync_scheduled_task_canceled(db, run)
        return True

    @staticmethod
    def _build_executor_cancel_status(
        *,
        has_active_runs: bool,
    ) -> Literal["not_required", "pending"]:
        return "pending" if has_active_runs else "not_required"

    @classmethod
    def _requires_manager_side_cancellation(
        cls,
        *,
        db_session: AgentSession,
        has_active_runs: bool,
        has_any_runs: bool,
    ) -> bool:
        if has_active_runs or cls._has_pending_cancellation(db_session):
            return True
        return not has_any_runs and db_session.status in {"pending", "running"}

    @staticmethod
    def _build_session_cancel_response(
        *,
        db_session: AgentSession,
        canceled_runs: int,
        canceled_queue_items: int,
        expired_requests: int,
        executor_cancel_status: Literal["not_required", "pending", "completed"],
    ) -> SessionCancelResponse:
        return SessionCancelResponse(
            session_id=db_session.id,
            status=db_session.status,
            canceled_runs=canceled_runs,
            canceled_queued_queries=canceled_queue_items,
            expired_user_input_requests=expired_requests,
            executor_cancel_status=executor_cancel_status,
            executor_cancel_target_worker_id=db_session.cancellation_target_worker_id,
            executor_cancelled=executor_cancel_status == "completed",
        )

    def create_session(
        self, db: Session, user_id: str, request: SessionCreateRequest
    ) -> AgentSession:
        """Creates a new session."""
        config_dict = (
            request.config.model_dump(exclude_unset=True) if request.config else None
        )
        project_id = request.project_id
        if project_id is not None:
            project = ProjectRepository.get_by_id(db, project_id)
            if not project or project.user_id != user_id:
                raise AppException(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    message=f"Project not found: {project_id}",
                )

        db_session = SessionRepository.create(
            session_db=db,
            user_id=user_id,
            config=config_dict,
            project_id=project_id,
            kind="chat",
        )

        db.commit()
        db.refresh(db_session)

        logger.info(f"Created session {db_session.id} for user {user_id}")
        return db_session

    def get_session(self, db: Session, session_id: uuid.UUID) -> AgentSession:
        """Gets a session by ID.

        Raises:
            AppException: If session not found.
        """
        db_session = SessionRepository.get_by_id(db, session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )
        return db_session

    def update_session(
        self, db: Session, session_id: uuid.UUID, request: SessionUpdateRequest
    ) -> AgentSession:
        """Updates session fields."""
        db_session = self.get_session(db, session_id)
        if "project_id" in request.model_fields_set:
            project_id = request.project_id
            if project_id is None:
                db_session.project_id = None
            else:
                project = ProjectRepository.get_by_id(db, project_id)
                if not project or project.user_id != db_session.user_id:
                    raise AppException(
                        error_code=ErrorCode.PROJECT_NOT_FOUND,
                        message=f"Project not found: {project_id}",
                    )
                db_session.project_id = project_id

        if "config" in request.model_fields_set and request.config is not None:
            base_config = self._deepcopy_json(db_session.config_snapshot) or {}
            merged_config = task_service._build_config_snapshot(  # noqa: SLF001
                db,
                db_session.user_id,
                request.config,
                base_config=base_config,
            )
            project = (
                ProjectRepository.get_by_id(db, db_session.project_id)
                if db_session.project_id is not None
                else None
            )
            db_session.config_snapshot = (
                task_service._apply_project_repo_defaults(  # noqa: SLF001
                    merged_config,
                    project,
                )
                or None
            )

        if "title" in request.model_fields_set:
            if request.title is None:
                db_session.title = None
            else:
                title = request.title.strip()
                if not title:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message="Title cannot be empty",
                    )
                if len(title) > 255:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message="Title exceeds maximum length (255)",
                    )
                db_session.title = title

        if "is_pinned" in request.model_fields_set:
            if request.is_pinned:
                if not db_session.is_pinned:
                    db_session.is_pinned = True
                    db_session.pinned_at = datetime.now(timezone.utc)
            else:
                db_session.is_pinned = False
                db_session.pinned_at = None

        if request.status is not None:
            next_status = request.status
            if db_session.status in {"canceling", "canceled"} and next_status in {
                "pending",
                "running",
                "completed",
                "failed",
            }:
                next_status = db_session.status
            db_session.status = next_status
        if request.sdk_session_id is not None:
            db_session.sdk_session_id = request.sdk_session_id
        if request.workspace_archive_url is not None:
            db_session.workspace_archive_url = request.workspace_archive_url
        if request.state_patch is not None:
            db_session.state_patch = request.state_patch
        if request.workspace_files_prefix is not None:
            db_session.workspace_files_prefix = request.workspace_files_prefix
        if request.workspace_manifest_key is not None:
            db_session.workspace_manifest_key = request.workspace_manifest_key
        if request.workspace_archive_key is not None:
            db_session.workspace_archive_key = request.workspace_archive_key
        if request.workspace_export_status is not None:
            db_session.workspace_export_status = request.workspace_export_status

        db.commit()
        db.refresh(db_session)

        logger.info(f"Updated session {session_id}")
        return db_session

    def delete_session(self, db: Session, session_id: uuid.UUID) -> AgentSession:
        """Soft deletes a session."""
        db_session = self.get_session(db, session_id)
        db_session.is_deleted = True

        db.commit()
        db.refresh(db_session)

        logger.info(f"Soft deleted session {session_id}")
        return db_session

    def list_sessions(
        self,
        db: Session,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        project_id: uuid.UUID | None = None,
        *,
        kind: str | None = None,
    ) -> list[AgentSession]:
        """Lists sessions, optionally filtered by user."""
        if user_id:
            return SessionRepository.list_by_user(
                db, user_id, limit, offset, project_id, kind=kind
            )
        return SessionRepository.list_all(db, limit, offset, project_id, kind=kind)

    def find_session_by_sdk_id_or_uuid(
        self, db: Session, session_id: str
    ) -> AgentSession | None:
        """Finds session by SDK session ID or UUID."""
        db_session = SessionRepository.get_by_sdk_session_id(db, session_id)

        if not db_session:
            try:
                session_uuid = uuid.UUID(session_id)
                db_session = SessionRepository.get_by_id(db, session_uuid)
            except ValueError:
                pass

        return db_session

    def cancel_session(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        user_id: str,
        reason: str | None = None,
    ) -> SessionCancelResponse:
        """Cancel a session and wait for manager-side executor shutdown when needed."""
        db_session = SessionRepository.get_by_id_for_update(db, session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )
        if db_session.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )

        now = datetime.now(timezone.utc)
        runs = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(
                AgentRun.status.in_(
                    [
                        *self.QUEUED_RUN_STATUSES,
                        *self.ACTIVE_CANCELLATION_RUN_STATUSES,
                    ]
                )
            )
            .order_by(AgentRun.created_at.desc())
            .all()
        )
        queued_runs = [run for run in runs if run.status in self.QUEUED_RUN_STATUSES]
        active_runs = [
            run for run in runs if run.status in self.ACTIVE_CANCELLATION_RUN_STATUSES
        ]

        canceled_runs = 0
        for run in queued_runs:
            if self._mark_run_canceled(db, run, now=now, clear_claim=True):
                canceled_runs += 1

        for run in active_runs:
            if run.status != "canceling":
                run.status = "canceling"

        canceled_queue_items = SessionQueueItemRepository.mark_canceled(
            db, session_id=session_id
        )

        pending_requests = UserInputRequestRepository.list_pending_by_session(
            db, session_id
        )
        expired_requests = 0
        for entry in pending_requests:
            entry.status = "expired"
            entry.expires_at = now
            expired_requests += 1

        self._mark_tool_executions_canceled(
            executions=ToolExecutionRepository.list_unfinished_by_session(
                db,
                session_id,
            ),
            now=now,
            reason=reason,
        )

        has_active_runs = bool(active_runs)
        requires_manager_side_cancellation = self._requires_manager_side_cancellation(
            db_session=db_session,
            has_active_runs=has_active_runs,
            has_any_runs=bool(runs),
        )
        executor_cancel_status = self._build_executor_cancel_status(
            has_active_runs=requires_manager_side_cancellation
        )
        if requires_manager_side_cancellation:
            if not self._has_pending_cancellation(db_session):
                target_run = active_runs[0] if active_runs else None
                target_worker_id = next(
                    (
                        run.claimed_by
                        for run in active_runs
                        if isinstance(run.claimed_by, str) and run.claimed_by.strip()
                    ),
                    None,
                )
                db_session.cancellation_requested_at = now
                db_session.cancellation_target_run_id = (
                    target_run.id if target_run else None
                )
                db_session.cancellation_target_worker_id = target_worker_id
                db_session.cancellation_claimed_by = None
                db_session.cancellation_lease_expires_at = None
                db_session.cancellation_completed_at = None
                db_session.cancellation_error = None
            if reason is not None:
                db_session.cancellation_reason = reason.strip() or None
            db_session.status = "canceling"
        else:
            SessionQueueService.clear_cancellation_state(db_session)
            db_session.status = "canceled"

        db.commit()
        db.refresh(db_session)

        return self._build_session_cancel_response(
            db_session=db_session,
            canceled_runs=canceled_runs,
            canceled_queue_items=canceled_queue_items,
            expired_requests=expired_requests,
            executor_cancel_status=executor_cancel_status,
        )

    def claim_next_cancellation(
        self,
        db: Session,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> SessionCancellationClaimResponse | None:
        """Claim the next pending session cancellation for a manager worker."""
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="worker_id cannot be empty",
            )

        lease_seconds = max(5, int(lease_seconds))
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)

        db_session = (
            db.query(AgentSession)
            .filter(AgentSession.status == "canceling")
            .filter(AgentSession.cancellation_requested_at.isnot(None))
            .filter(AgentSession.cancellation_completed_at.is_(None))
            .filter(
                or_(
                    AgentSession.cancellation_target_worker_id == normalized_worker_id,
                    AgentSession.cancellation_target_worker_id.is_(None),
                )
            )
            .filter(
                or_(
                    AgentSession.cancellation_claimed_by.is_(None),
                    AgentSession.cancellation_lease_expires_at.is_(None),
                    AgentSession.cancellation_lease_expires_at < now,
                )
            )
            .order_by(AgentSession.cancellation_requested_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if db_session is None:
            db.commit()
            return None

        db_session.cancellation_claimed_by = normalized_worker_id
        db_session.cancellation_lease_expires_at = lease_until
        db.commit()
        db.refresh(db_session)

        return SessionCancellationClaimResponse(
            session_id=db_session.id,
            run_id=db_session.cancellation_target_run_id,
            worker_id=db_session.cancellation_target_worker_id,
            reason=db_session.cancellation_reason,
            requested_at=db_session.cancellation_requested_at or now,
        )

    def complete_cancellation(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        worker_id: str,
        stop_status: str,
        message: str | None = None,
    ) -> SessionCancellationCompleteResponse:
        """Finalize or release a claimed session cancellation."""
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="worker_id cannot be empty",
            )

        db_session = SessionRepository.get_by_id_for_update(db, session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )
        if not self._has_pending_cancellation(db_session):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session has no pending cancellation request",
            )
        if db_session.cancellation_claimed_by not in {None, normalized_worker_id}:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cancellation is claimed by another worker",
            )

        stop_status_value = stop_status.strip().lower()
        if stop_status_value not in {"stopped", "not_found", "failed"}:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid stop_status: {stop_status}",
            )

        now = datetime.now(timezone.utc)
        if stop_status_value == "failed":
            db_session.cancellation_claimed_by = None
            db_session.cancellation_lease_expires_at = None
            db_session.cancellation_error = (message or "Executor stop failed").strip()
            db.commit()
            db.refresh(db_session)
            return SessionCancellationCompleteResponse(
                session_id=db_session.id,
                status=db_session.status,
                stop_status=stop_status_value,
                canceled_runs=0,
            )

        runs = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(AgentRun.status.in_(["canceling", "claimed", "running"]))
            .all()
        )
        canceled_runs = 0
        for run in runs:
            if self._mark_run_canceled(db, run, now=now, clear_claim=True):
                canceled_runs += 1

        db_session.status = "canceled"
        db_session.cancellation_completed_at = now
        db_session.cancellation_claimed_by = None
        db_session.cancellation_lease_expires_at = None
        db_session.cancellation_error = None

        db.commit()
        db.refresh(db_session)

        return SessionCancellationCompleteResponse(
            session_id=db_session.id,
            status=db_session.status,
            stop_status=stop_status_value,
            canceled_runs=canceled_runs,
        )

    def branch_session(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        user_id: str,
        cutoff_message_id: int,
    ) -> AgentSession:
        """Create a new branched session by cloning history up to a message checkpoint."""
        source_session = self.get_session(db, session_id)
        if source_session.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )
        self._ensure_no_active_queue_items(db, source_session.id)

        cutoff_message = MessageRepository.get_by_id(db, cutoff_message_id)
        if not cutoff_message:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Message not found: {cutoff_message_id}",
            )
        if cutoff_message.session_id != source_session.id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="message_id does not belong to the session",
            )

        next_user_message_id_after_cutoff: int | None = None
        if cutoff_message.role == "assistant":
            # "Real" user turns are defined by runs.user_message_id.
            next_user_run_after_cutoff = (
                db.query(AgentRun.user_message_id)
                .filter(AgentRun.session_id == session_id)
                .filter(AgentRun.user_message_id > cutoff_message_id)
                .order_by(AgentRun.user_message_id.asc())
                .first()
            )
            if next_user_run_after_cutoff is not None:
                next_user_message_id_after_cutoff = int(next_user_run_after_cutoff[0])

        branched_session = SessionRepository.create(
            session_db=db,
            user_id=source_session.user_id,
            config=self._deepcopy_json(source_session.config_snapshot),
            project_id=source_session.project_id,
            kind=source_session.kind,
        )
        db.flush()

        # Copy session-level metadata and latest exported workspace snapshot.
        branched_session.title = source_session.title
        branched_session.status = "completed"
        branched_session.workspace_archive_url = source_session.workspace_archive_url
        branched_session.state_patch = self._deepcopy_json(source_session.state_patch)
        branched_session.workspace_files_prefix = source_session.workspace_files_prefix
        branched_session.workspace_manifest_key = source_session.workspace_manifest_key
        branched_session.workspace_archive_key = source_session.workspace_archive_key
        branched_session.workspace_export_status = (
            source_session.workspace_export_status
        )
        # Start a new SDK thread when users continue in the branch.
        branched_session.sdk_session_id = None

        source_messages_query = (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
        )
        if cutoff_message.role == "assistant":
            if next_user_message_id_after_cutoff is not None:
                # Keep a complete assistant turn: copy until the next user prompt.
                source_messages_query = source_messages_query.filter(
                    AgentMessage.id < next_user_message_id_after_cutoff
                )
            # If there is no next user prompt, keep all remaining assistant-side events.
        else:
            source_messages_query = source_messages_query.filter(
                AgentMessage.id <= cutoff_message_id
            )
        source_messages = source_messages_query.all()
        if not source_messages:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="No messages available before the checkpoint",
            )

        message_id_map: dict[int, int] = {}
        copied_user_message_ids: set[int] = set()

        for source_message in source_messages:
            branched_message = MessageRepository.create(
                session_db=db,
                session_id=branched_session.id,
                role=source_message.role,
                content=self._deepcopy_json(source_message.content),
                text_preview=source_message.text_preview,
            )
            db.flush()
            message_id_map[source_message.id] = branched_message.id
            if source_message.role == "user":
                copied_user_message_ids.add(source_message.id)

        run_id_map: dict[uuid.UUID, uuid.UUID] = {}
        if copied_user_message_ids:
            source_runs = (
                db.query(AgentRun)
                .filter(AgentRun.session_id == session_id)
                .filter(AgentRun.user_message_id.in_(copied_user_message_ids))
                .order_by(AgentRun.scheduled_at.asc(), AgentRun.created_at.asc())
                .all()
            )
            for source_run in source_runs:
                if source_run.status not in {"completed", "failed", "canceled"}:
                    continue
                target_user_message_id = message_id_map.get(source_run.user_message_id)
                if target_user_message_id is None:
                    continue

                branched_run = RunRepository.create(
                    session_db=db,
                    session_id=branched_session.id,
                    user_message_id=target_user_message_id,
                    permission_mode=source_run.permission_mode,
                    schedule_mode=source_run.schedule_mode,
                    scheduled_at=source_run.scheduled_at,
                    config_snapshot=self._deepcopy_json(source_run.config_snapshot),
                )
                branched_run.status = source_run.status
                branched_run.progress = source_run.progress
                branched_run.state_patch = self._deepcopy_json(source_run.state_patch)
                branched_run.scheduled_task_id = None
                branched_run.claimed_by = None
                branched_run.lease_expires_at = None
                branched_run.attempts = source_run.attempts
                branched_run.last_error = source_run.last_error
                branched_run.started_at = source_run.started_at
                branched_run.finished_at = source_run.finished_at
                branched_run.workspace_archive_url = source_run.workspace_archive_url
                branched_run.workspace_files_prefix = source_run.workspace_files_prefix
                branched_run.workspace_manifest_key = source_run.workspace_manifest_key
                branched_run.workspace_archive_key = source_run.workspace_archive_key
                branched_run.workspace_export_status = (
                    source_run.workspace_export_status
                )
                db.flush()
                run_id_map[source_run.id] = branched_run.id

        source_usage_logs = (
            db.query(UsageLog)
            .filter(UsageLog.session_id == session_id)
            .order_by(UsageLog.created_at.asc())
            .all()
        )
        for source_log in source_usage_logs:
            target_run_id: uuid.UUID | None = None
            if source_log.run_id is not None:
                target_run_id = run_id_map.get(source_log.run_id)
                if target_run_id is None:
                    continue
            UsageLogRepository.create(
                session_db=db,
                session_id=branched_session.id,
                run_id=target_run_id,
                duration_ms=source_log.duration_ms,
                input_tokens=source_log.input_tokens,
                output_tokens=source_log.output_tokens,
                cache_creation_input_tokens=source_log.cache_creation_input_tokens,
                cache_read_input_tokens=source_log.cache_read_input_tokens,
                total_tokens=source_log.total_tokens,
                include_in_user_analytics=False,
                usage_json=self._deepcopy_json(source_log.usage_json),
            )

        db.commit()
        db.refresh(branched_session)

        logger.info(
            "Created branched session %s from source %s at message %s",
            branched_session.id,
            source_session.id,
            cutoff_message_id,
        )
        return branched_session

    def regenerate_from_message(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        user_id: str,
        user_message_id: int,
        assistant_message_id: int,
        model: str | None = None,
        model_provider_id: str | None = None,
    ) -> TaskEnqueueResponse:
        """Regenerate a prior turn by trimming subsequent history in-place."""
        db_session = self.get_session(db, session_id)
        if db_session.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )
        self._ensure_session_not_canceling(db_session)
        self._ensure_no_active_queue_items(db, db_session.id)

        user_message = MessageRepository.get_by_id(db, user_message_id)
        if (
            not user_message
            or user_message.session_id != db_session.id
            or user_message.role != "user"
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="user_message_id is invalid for this session",
            )

        assistant_message = MessageRepository.get_by_id(db, assistant_message_id)
        if (
            not assistant_message
            or assistant_message.session_id != db_session.id
            or assistant_message.role != "assistant"
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="assistant_message_id is invalid for this session",
            )
        if assistant_message.id <= user_message.id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="assistant_message_id must be after user_message_id",
            )

        latest_target_run = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == db_session.id)
            .filter(AgentRun.user_message_id == user_message_id)
            .order_by(AgentRun.created_at.desc())
            .first()
        )
        permission_mode = (
            latest_target_run.permission_mode if latest_target_run else "default"
        )
        run_config_snapshot = dict(
            self._deepcopy_json(db_session.config_snapshot) or {}
        )
        if latest_target_run and isinstance(latest_target_run.config_snapshot, dict):
            input_files = latest_target_run.config_snapshot.get("input_files")
            if isinstance(input_files, list):
                run_config_snapshot["input_files"] = self._deepcopy_json(input_files)
        # Override model with current selection if provided
        if model is not None:
            run_config_snapshot["model"] = model
        if model_provider_id is not None:
            run_config_snapshot["model_provider_id"] = model_provider_id

        runs_to_delete = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == db_session.id)
            .filter(AgentRun.user_message_id >= user_message_id)
            .all()
        )
        for run in runs_to_delete:
            db.delete(run)

        messages_to_delete = (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == db_session.id)
            .filter(AgentMessage.id >= assistant_message_id)
            .all()
        )
        for message in messages_to_delete:
            db.delete(message)

        pending_requests = UserInputRequestRepository.list_pending_by_session(
            db, db_session.id
        )
        now = datetime.now(timezone.utc)
        for entry in pending_requests:
            entry.status = "expired"
            entry.expires_at = now

        db.flush()

        db_run = RunRepository.create(
            session_db=db,
            session_id=db_session.id,
            user_message_id=user_message_id,
            permission_mode=permission_mode,
            schedule_mode="immediate",
            config_snapshot=run_config_snapshot or None,
        )
        SessionQueueService.clear_cancellation_state(db_session)
        db_session.state_patch = {}
        db_session.status = "pending"

        db.commit()
        db.refresh(db_run)

        logger.info(
            "Regenerated session %s from user_message=%s assistant_message=%s run=%s",
            db_session.id,
            user_message_id,
            assistant_message_id,
            db_run.id,
        )
        return TaskEnqueueResponse(
            session_id=db_session.id,
            run_id=db_run.id,
            status=db_run.status,
        )

    def edit_message_and_regenerate(
        self,
        db: Session,
        session_id: uuid.UUID,
        *,
        user_id: str,
        user_message_id: int,
        content: str,
        model: str | None = None,
        model_provider_id: str | None = None,
    ) -> TaskEnqueueResponse:
        """Replace a user message then regenerate by deleting all later history."""
        db_session = self.get_session(db, session_id)
        if db_session.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )
        self._ensure_session_not_canceling(db_session)
        self._ensure_no_active_queue_items(db, db_session.id)

        user_message = MessageRepository.get_by_id(db, user_message_id)
        if (
            not user_message
            or user_message.session_id != db_session.id
            or user_message.role != "user"
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="user_message_id is invalid for this session",
            )

        prompt = content.strip()
        if not prompt:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="content cannot be empty",
            )

        latest_target_run = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == db_session.id)
            .filter(AgentRun.user_message_id == user_message_id)
            .order_by(AgentRun.created_at.desc())
            .first()
        )
        permission_mode = (
            latest_target_run.permission_mode if latest_target_run else "default"
        )
        run_config_snapshot = dict(
            self._deepcopy_json(db_session.config_snapshot) or {}
        )
        if latest_target_run and isinstance(latest_target_run.config_snapshot, dict):
            input_files = latest_target_run.config_snapshot.get("input_files")
            if isinstance(input_files, list):
                run_config_snapshot["input_files"] = self._deepcopy_json(input_files)
        # Override model with current selection if provided
        if model is not None:
            run_config_snapshot["model"] = model
        if model_provider_id is not None:
            run_config_snapshot["model_provider_id"] = model_provider_id

        user_message.content = {
            "_type": "UserMessage",
            "content": [{"_type": "TextBlock", "text": prompt}],
        }
        user_message.text_preview = prompt[:500]

        runs_to_delete = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == db_session.id)
            .filter(AgentRun.user_message_id >= user_message_id)
            .all()
        )
        for run in runs_to_delete:
            db.delete(run)

        messages_to_delete = (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == db_session.id)
            .filter(AgentMessage.id > user_message_id)
            .all()
        )
        for message in messages_to_delete:
            db.delete(message)

        pending_requests = UserInputRequestRepository.list_pending_by_session(
            db, db_session.id
        )
        now = datetime.now(timezone.utc)
        for entry in pending_requests:
            entry.status = "expired"
            entry.expires_at = now

        db.flush()

        db_run = RunRepository.create(
            session_db=db,
            session_id=db_session.id,
            user_message_id=user_message_id,
            permission_mode=permission_mode,
            schedule_mode="immediate",
            config_snapshot=run_config_snapshot or None,
        )
        SessionQueueService.clear_cancellation_state(db_session)
        db_session.state_patch = {}
        db_session.status = "pending"
        # Start a fresh upstream SDK thread, otherwise removed turns may still affect context.
        db_session.sdk_session_id = None

        db.commit()
        db.refresh(db_run)

        logger.info(
            "Edited and regenerated session %s from user_message=%s run=%s",
            db_session.id,
            user_message_id,
            db_run.id,
        )
        return TaskEnqueueResponse(
            session_id=db_session.id,
            run_id=db_run.id,
            status=db_run.status,
        )
