from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.repositories.session_repository import SessionRepository
from app.services.session_queue_service import SessionQueueService


class RunLifecycleService:
    TERMINAL_STATUSES = {"completed", "failed", "canceled"}

    def __init__(self) -> None:
        self._session_queue_service = SessionQueueService()

    def _sync_scheduled_task_last_status(self, db: Session, db_run: AgentRun) -> None:
        if not db_run.scheduled_task_id:
            return

        db_task = ScheduledTaskRepository.get_by_id(db, db_run.scheduled_task_id)
        if not db_task:
            return

        if db_task.last_run_id and db_task.last_run_id != db_run.id:
            return

        db_task.last_run_id = db_run.id
        db_task.last_run_status = db_run.status

        if db_run.status == "failed":
            db_task.last_error = db_run.last_error or db_task.last_error
        elif db_run.status in {"completed", "canceled"}:
            db_task.last_error = None

    def mark_running(self, db: Session, db_run: AgentRun) -> AgentSession | None:
        db_session = SessionRepository.get_by_id_for_update(db, db_run.session_id)
        if not db_session:
            return None

        if db_run.status in self.TERMINAL_STATUSES:
            return db_session

        now = datetime.now(timezone.utc)
        if db_run.status in {"queued", "claimed"}:
            self._session_queue_service.clear_execution_state(db_session)
            db_run.status = "running"
        if db_run.started_at is None:
            db_run.started_at = now
        db_run.lease_expires_at = None

        if db_session.status != "canceled":
            db_session.status = "running"

        self._sync_scheduled_task_last_status(db, db_run)
        db.flush()
        return db_session

    def finalize_terminal(
        self,
        db: Session,
        db_run: AgentRun,
        *,
        status: str,
        error_message: str | None = None,
    ) -> tuple[AgentSession | None, AgentRun | None]:
        db_session = SessionRepository.get_by_id_for_update(db, db_run.session_id)
        if not db_session:
            return None, None

        if db_run.status in self.TERMINAL_STATUSES:
            if status == "failed" and error_message and not db_run.last_error:
                db_run.last_error = error_message
            self._sync_scheduled_task_last_status(db, db_run)
            db.flush()
            return db_session, None

        now = datetime.now(timezone.utc)
        db_run.status = status
        if db_run.finished_at is None:
            db_run.finished_at = now
        db_run.lease_expires_at = None

        promoted_run: AgentRun | None = None
        if status == "completed":
            db_run.progress = 100
            db_run.last_error = None
            promoted_run = self._session_queue_service.promote_next_if_available(
                db, db_session
            )
            if promoted_run is None:
                db_session.status = "completed"
        elif status == "failed":
            if error_message:
                db_run.last_error = error_message
            self._session_queue_service.pause_active_items(db, db_session.id)
            db_session.status = "failed"
        elif status == "canceled":
            self._session_queue_service.cancel_active_items(db, db_session.id)
            db_session.status = "canceled"

        self._sync_scheduled_task_last_status(db, db_run)
        db.flush()
        return db_session, promoted_run
