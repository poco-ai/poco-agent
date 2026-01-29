import logging
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from croniter import croniter
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_run import AgentRun
from app.models.agent_scheduled_task import AgentScheduledTask
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.scheduled_task import (
    ScheduledTaskCreateRequest,
    ScheduledTaskDispatchResponse,
    ScheduledTaskResponse,
    ScheduledTaskTriggerResponse,
    ScheduledTaskUpdateRequest,
)
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class ScheduledTaskService:
    """Service layer for scheduled task management and dispatch."""

    def __init__(self) -> None:
        self._task_service = TaskService()

    @staticmethod
    def _validate_cron(expr: str) -> str:
        value = (expr or "").strip()
        if not value:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="cron cannot be empty",
            )
        if not croniter.is_valid(value):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid cron expression: {value}",
            )
        return value

    @staticmethod
    def _validate_timezone(tz_name: str | None) -> str:
        value = (tz_name or "").strip() or "UTC"
        try:
            _ = ZoneInfo(value)
        except Exception as e:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid timezone: {value}",
            ) from e
        return value

    def _compute_next_run_at(
        self,
        *,
        cron_expr: str,
        timezone_name: str,
        now_utc: datetime,
    ) -> datetime:
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        tz = ZoneInfo(timezone_name)
        base = now_utc.astimezone(tz)
        itr = croniter(cron_expr, base)
        next_local = itr.get_next(datetime)
        if isinstance(next_local, datetime) and next_local.tzinfo is None:
            next_local = next_local.replace(tzinfo=tz)
        if not isinstance(next_local, datetime):
            raise AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to compute next_run_at",
            )
        return next_local.astimezone(timezone.utc)

    @staticmethod
    def _normalize_name(value: str) -> str:
        name = (value or "").strip()
        if not name:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="name cannot be empty",
            )
        return name

    @staticmethod
    def _normalize_prompt(value: str) -> str:
        prompt = (value or "").strip()
        if not prompt:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="prompt cannot be empty",
            )
        return prompt

    @staticmethod
    def _build_user_message_content(prompt: str) -> dict:
        return {
            "_type": "UserMessage",
            "content": [{"_type": "TextBlock", "text": prompt}],
        }

    def create_task(
        self, db: Session, user_id: str, request: ScheduledTaskCreateRequest
    ) -> ScheduledTaskResponse:
        name = self._normalize_name(request.name)
        prompt = self._normalize_prompt(request.prompt)
        cron_expr = self._validate_cron(request.cron)
        tz_name = self._validate_timezone(request.timezone)

        # Build a pinned config snapshot using existing TaskService merge logic
        config_snapshot = (
            self._task_service._build_config_snapshot(  # noqa: SLF001
                db,
                user_id,
                request.config,
                base_config={},
            )
            or {}
        )
        input_files = (
            [f.model_dump(mode="json") for f in request.config.input_files]
            if request.config and request.config.input_files
            else []
        )

        project_id = request.project_id
        if project_id is not None:
            project = ProjectRepository.get_by_id(db, project_id)
            if not project or project.user_id != user_id:
                raise AppException(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    message=f"Project not found: {project_id}",
                )

        session_id: uuid.UUID | None = None
        if request.reuse_session:
            db_session = SessionRepository.create(
                session_db=db,
                user_id=user_id,
                config=config_snapshot,
                project_id=project_id,
                kind="scheduled",
            )
            db.flush()
            session_id = db_session.id

        now_utc = datetime.now(timezone.utc)
        next_run_at = self._compute_next_run_at(
            cron_expr=cron_expr, timezone_name=tz_name, now_utc=now_utc
        )

        db_task = ScheduledTaskRepository.create(
            db,
            user_id=user_id,
            name=name,
            cron=cron_expr,
            timezone_name=tz_name,
            prompt=prompt,
            enabled=bool(request.enabled),
            reuse_session=bool(request.reuse_session),
            session_id=session_id,
            config_snapshot=config_snapshot,
            input_files=input_files or None,
            next_run_at=next_run_at,
        )

        db.commit()
        db.refresh(db_task)

        logger.info(
            "scheduled_task_created",
            extra={
                "scheduled_task_id": str(db_task.id),
                "user_id": user_id,
                "reuse_session": bool(db_task.reuse_session),
                "session_id": str(db_task.session_id) if db_task.session_id else None,
            },
        )
        return ScheduledTaskResponse.model_validate(db_task)

    def list_tasks(
        self, db: Session, user_id: str, *, limit: int = 100, offset: int = 0
    ) -> list[ScheduledTaskResponse]:
        tasks = ScheduledTaskRepository.list_by_user(
            db, user_id, limit=limit, offset=offset
        )
        return [ScheduledTaskResponse.model_validate(t) for t in tasks]

    def get_task(
        self, db: Session, user_id: str, task_id: uuid.UUID
    ) -> ScheduledTaskResponse:
        db_task = ScheduledTaskRepository.get_by_id(db, task_id)
        if not db_task:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Scheduled task not found: {task_id}",
            )
        if db_task.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Scheduled task does not belong to the user",
            )
        return ScheduledTaskResponse.model_validate(db_task)

    def update_task(
        self,
        db: Session,
        user_id: str,
        task_id: uuid.UUID,
        request: ScheduledTaskUpdateRequest,
    ) -> ScheduledTaskResponse:
        db_task = ScheduledTaskRepository.get_by_id(db, task_id)
        if not db_task:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Scheduled task not found: {task_id}",
            )
        if db_task.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Scheduled task does not belong to the user",
            )

        recompute = False
        if request.name is not None:
            db_task.name = self._normalize_name(request.name)
        if request.prompt is not None:
            db_task.prompt = self._normalize_prompt(request.prompt)
        if request.enabled is not None:
            db_task.enabled = bool(request.enabled)
        if request.cron is not None:
            db_task.cron = self._validate_cron(request.cron)
            recompute = True
        if request.timezone is not None:
            db_task.timezone = self._validate_timezone(request.timezone)
            recompute = True

        if recompute:
            now_utc = datetime.now(timezone.utc)
            db_task.next_run_at = self._compute_next_run_at(
                cron_expr=db_task.cron,
                timezone_name=db_task.timezone,
                now_utc=now_utc,
            )

        db.commit()
        db.refresh(db_task)
        return ScheduledTaskResponse.model_validate(db_task)

    def delete_task(self, db: Session, user_id: str, task_id: uuid.UUID) -> None:
        db_task = ScheduledTaskRepository.get_by_id(db, task_id)
        if not db_task:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Scheduled task not found: {task_id}",
            )
        if db_task.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Scheduled task does not belong to the user",
            )
        ScheduledTaskRepository.soft_delete(db, task_id)
        db.commit()

    def trigger_task(
        self, db: Session, user_id: str, task_id: uuid.UUID
    ) -> ScheduledTaskTriggerResponse:
        db_task = ScheduledTaskRepository.get_by_id(db, task_id)
        if not db_task:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Scheduled task not found: {task_id}",
            )
        if db_task.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Scheduled task does not belong to the user",
            )
        run = self._enqueue_run_for_task(
            db,
            task=db_task,
            scheduled_at=datetime.now(timezone.utc),
            force=True,
        )
        if not run:
            raise AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to enqueue scheduled task run",
            )
        db_task.last_run_id = run.id
        db_task.last_run_status = run.status
        db_task.last_error = None
        db.commit()
        db.refresh(db_task)
        db.refresh(run)
        return ScheduledTaskTriggerResponse(session_id=run.session_id, run_id=run.id)

    def dispatch_due(
        self,
        db: Session,
        *,
        limit: int = 50,
    ) -> ScheduledTaskDispatchResponse:
        now_utc = datetime.now(timezone.utc)
        tasks = ScheduledTaskRepository.claim_due_for_update(
            db, limit=limit, now_utc=now_utc
        )

        dispatched: list[uuid.UUID] = []
        skipped = 0
        errors = 0

        for task in tasks:
            try:
                # Only dispatch when no active/queued run is present for this task/session.
                run = self._enqueue_run_for_task(
                    db,
                    task=task,
                    scheduled_at=task.next_run_at,
                    force=False,
                )
                if not run:
                    skipped += 1
                    # Coalesce missed executions when an active run already exists.
                    # Otherwise the task remains due and will be re-claimed every dispatch cycle.
                    task.next_run_at = self._compute_next_run_at(
                        cron_expr=task.cron,
                        timezone_name=task.timezone,
                        now_utc=now_utc,
                    )
                    continue

                task.last_run_id = run.id
                task.last_run_status = run.status
                task.last_error = None
                task.next_run_at = self._compute_next_run_at(
                    cron_expr=task.cron,
                    timezone_name=task.timezone,
                    now_utc=now_utc,
                )
                dispatched.append(run.id)
            except Exception as e:
                errors += 1
                task.last_error = str(e)
                logger.exception(
                    "scheduled_task_dispatch_failed",
                    extra={"scheduled_task_id": str(task.id)},
                )
                # If a pinned session is missing, disable the task to avoid infinite failures.
                if task.reuse_session and task.session_id is not None:
                    db_session = SessionRepository.get_by_id(db, task.session_id)
                    if not db_session:
                        task.enabled = False

        db.commit()

        return ScheduledTaskDispatchResponse(
            dispatched=len(dispatched),
            run_ids=dispatched,
            skipped=skipped,
            errors=errors,
        )

    def _enqueue_run_for_task(
        self,
        db: Session,
        *,
        task: AgentScheduledTask,
        scheduled_at: datetime,
        force: bool,
    ) -> AgentRun | None:
        """Create (message, run) for a scheduled task.

        Returns:
            AgentRun instance when enqueued, or None when skipped.
        """
        prompt = self._normalize_prompt(task.prompt)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        scheduled_at = scheduled_at.astimezone(timezone.utc)

        session_id: uuid.UUID
        if task.reuse_session:
            if not task.session_id:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="reuse_session=true but session_id is missing",
                )
            db_session = SessionRepository.get_by_id(db, task.session_id)
            if not db_session:
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session not found: {task.session_id}",
                )
            session_id = db_session.id
        else:
            # Create a fresh session/workspace for this run.
            db_session = SessionRepository.create(
                session_db=db,
                user_id=task.user_id,
                config=task.config_snapshot or {},
                project_id=None,
                kind="scheduled",
            )
            db.flush()
            session_id = db_session.id

        # Skip if an unfinished run already exists (avoid unbounded queue growth).
        if not force:
            existing_run = (
                db.query(AgentRun)
                .filter(AgentRun.session_id == session_id)
                .filter(AgentRun.status.in_(["queued", "claimed", "running"]))
                .order_by(AgentRun.created_at.desc())
                .first()
            )
            if existing_run:
                return None

        # Clear previous execution state so the UI doesn't show stale file changes.
        db_session.state_patch = {}
        db_session.status = "pending"

        user_message_content = self._build_user_message_content(prompt)
        db_message = MessageRepository.create(
            session_db=db,
            session_id=session_id,
            role="user",
            content=user_message_content,
            text_preview=prompt[:500],
        )
        db.flush()

        run_snapshot = dict(task.config_snapshot or {})
        if task.input_files:
            run_snapshot["input_files"] = list(task.input_files)

        db_run = RunRepository.create(
            session_db=db,
            session_id=session_id,
            user_message_id=db_message.id,
            permission_mode="default",
            schedule_mode="scheduled",
            scheduled_at=scheduled_at,
            config_snapshot=run_snapshot or None,
        )
        db_run.scheduled_task_id = task.id
        db.flush()

        return db_run
