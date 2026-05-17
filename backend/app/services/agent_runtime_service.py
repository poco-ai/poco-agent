import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_persistent_state import AgentPersistentState
from app.repositories.agent_persistent_state_repository import (
    AgentPersistentStateRepository,
)
from app.repositories.run_repository import RunRepository
from app.repositories.session_queue_item_repository import (
    SessionQueueItemRepository,
)
from app.repositories.session_repository import SessionRepository


class AgentRuntimeService:
    LIVE_SESSION_STATUSES = {"pending", "running", "canceling"}

    @classmethod
    def _session_has_live_work(cls, db: Session, session_id: uuid.UUID) -> bool:
        session = SessionRepository.get_by_id(db, session_id)
        if session is not None and session.status in cls.LIVE_SESSION_STATUSES:
            return True
        if RunRepository.get_blocking_by_session(db, session_id) is not None:
            return True
        return SessionQueueItemRepository.has_active_items(db, session_id)

    @staticmethod
    def _terminal_runtime_status(db: Session, session_id: uuid.UUID) -> str:
        session = SessionRepository.get_by_id(db, session_id)
        if session is not None and session.status == "failed":
            return "failed"
        latest_terminal_run = RunRepository.get_latest_terminal_by_session(db, session_id)
        if latest_terminal_run is not None and latest_terminal_run.status == "failed":
            return "failed"
        return "idle"

    @staticmethod
    def _clear_runtime_binding(
        state: AgentPersistentState,
        *,
        runtime_status: str,
    ) -> AgentPersistentState:
        now = datetime.now(timezone.utc)
        state.runtime_status = runtime_status
        state.active_session_id = None
        state.active_task_id = None
        state.last_synced_at = now
        state.last_written_at = now
        return state

    def reconcile_persistent_state(
        self,
        db: Session,
        state: AgentPersistentState,
    ) -> AgentPersistentState:
        if state.runtime_status != "busy":
            return state
        if state.active_session_id is None:
            return self._clear_runtime_binding(state, runtime_status="idle")
        if self._session_has_live_work(db, state.active_session_id):
            return state
        return self._clear_runtime_binding(
            state,
            runtime_status=self._terminal_runtime_status(db, state.active_session_id),
        )

    @staticmethod
    def get_persistent_state(
        db: Session,
        agent_identity_id: uuid.UUID,
    ) -> AgentPersistentState:
        state = AgentPersistentStateRepository.get_by_agent_identity_id(
            db,
            agent_identity_id,
        )
        if state is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent persistent state not found: {agent_identity_id}",
            )
        return AgentRuntimeService().reconcile_persistent_state(db, state)

    def reserve_persistent_runtime(
        self,
        db: Session,
        *,
        agent_identity_id: uuid.UUID,
        session_id: uuid.UUID,
        channel_task_id: uuid.UUID | None,
    ) -> AgentPersistentState:
        state = self.get_persistent_state(db, agent_identity_id)
        if (
            state.runtime_status == "busy"
            and state.active_session_id is not None
            and state.active_session_id != session_id
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Agent persistent runtime is busy",
            )
        state.runtime_status = "busy"
        state.active_session_id = session_id
        state.active_task_id = channel_task_id
        state.last_synced_at = datetime.now(timezone.utc)
        return state

    def release_runtime_for_session(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        callback_status: str,
    ) -> AgentPersistentState | None:
        state = (
            db.query(AgentPersistentState)
            .filter(AgentPersistentState.active_session_id == session_id)
            .first()
        )
        if state is None:
            return None

        normalized = (callback_status or "").strip().lower()
        if normalized == "failed":
            return self._clear_runtime_binding(state, runtime_status="failed")
        if self._session_has_live_work(db, session_id):
            state.runtime_status = "busy"
            state.active_session_id = session_id
            state.last_synced_at = datetime.now(timezone.utc)
            return state
        return self._clear_runtime_binding(state, runtime_status="idle")
