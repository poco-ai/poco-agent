import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_assignment import AgentAssignment
from app.models.agent_identity import AgentIdentity
from app.models.persistent_runtime import PersistentRuntime
from app.repositories.agent_assignment_repository import AgentAssignmentRepository
from app.repositories.agent_persistent_state_repository import (
    AgentPersistentStateRepository,
)
from app.repositories.persistent_runtime_repository import (
    PersistentRuntimeRepository,
)
from app.repositories.run_repository import RunRepository
from app.repositories.session_queue_item_repository import (
    SessionQueueItemRepository,
)
from app.repositories.session_repository import SessionRepository
from app.schemas.persistent_runtime import (
    PersistentRuntimeControllerResponse,
    PersistentRuntimeResponse,
)


class PersistentRuntimeService:
    DEFAULT_SERVER_AGENT_IDLE_TIMEOUT_SECONDS = 15 * 60
    DEFAULT_SERVER_AGENT_WARM_RETENTION_SECONDS = 2 * 60
    DEFAULT_ASSIGNMENT_IDLE_TIMEOUT_SECONDS = 30 * 60
    DEFAULT_ASSIGNMENT_WARM_RETENTION_SECONDS = 5 * 60
    MAX_KEEPALIVE_SECONDS = 24 * 60 * 60
    LIVE_SESSION_STATUSES = {"pending", "running", "canceling"}

    @staticmethod
    def build_server_agent_runtime_key(agent_identity_id: uuid.UUID) -> str:
        return f"server_agent:{agent_identity_id}"

    @staticmethod
    def build_assignment_runtime_key(assignment_id: uuid.UUID) -> str:
        return f"agent_assignment:{assignment_id}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @classmethod
    def _session_has_live_work(cls, db: Session, session_id: uuid.UUID) -> bool:
        session = SessionRepository.get_by_id(db, session_id)
        if session is not None and session.status in cls.LIVE_SESSION_STATUSES:
            return True
        if RunRepository.get_blocking_by_session(db, session_id) is not None:
            return True
        return SessionQueueItemRepository.has_active_items(db, session_id)

    def get_by_runtime_key(self, db: Session, runtime_key: str) -> PersistentRuntime:
        runtime = PersistentRuntimeRepository.get_by_runtime_key(db, runtime_key)
        if runtime is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Persistent runtime not found: {runtime_key}",
            )
        return runtime

    def get_runtime(self, db: Session, runtime_key: str) -> PersistentRuntimeResponse:
        return PersistentRuntimeResponse.model_validate(
            self.get_by_runtime_key(db, runtime_key)
        )

    def build_server_agent_runtime_summary(
        self,
        db: Session,
        *,
        agent_identity: AgentIdentity,
    ) -> PersistentRuntimeResponse:
        runtime_key = self.build_server_agent_runtime_key(agent_identity.id)
        existing = PersistentRuntimeRepository.get_by_runtime_key(db, runtime_key)
        if existing is not None:
            return PersistentRuntimeResponse.model_validate(existing)

        persistent_state = agent_identity.persistent_state
        active_session_id = (
            persistent_state.active_session_id if persistent_state is not None else None
        )
        runtime_status = (
            (persistent_state.runtime_status or "").strip().lower()
            if persistent_state is not None
            else ""
        )
        lifecycle_state = "running" if runtime_status == "busy" else "sleeping"

        return PersistentRuntimeResponse(
            persistent_runtime_id=uuid.uuid4(),
            runtime_key=runtime_key,
            owner_type="server_agent",
            owner_id=agent_identity.id,
            agent_identity_id=agent_identity.id,
            assignment_id=None,
            session_id=active_session_id,
            container_id=None,
            lifecycle_state=lifecycle_state,
            auto_resume=True,
            idle_timeout_seconds=self.DEFAULT_SERVER_AGENT_IDLE_TIMEOUT_SECONDS,
            warm_retention_seconds=self.DEFAULT_SERVER_AGENT_WARM_RETENTION_SECONDS,
            keepalive_until=None,
            last_activity_at=(
                persistent_state.last_synced_at if persistent_state is not None else None
            ),
            last_started_at=None,
            last_stopped_at=None,
            last_stop_reason=None,
            worker_id=None,
            browser_enabled=False,
            filesystem_fingerprint=None,
            metadata_json=None,
            created_at=agent_identity.created_at,
            updated_at=agent_identity.updated_at,
        )

    def build_assignment_runtime_summary(
        self,
        db: Session,
        *,
        assignment: AgentAssignment,
    ) -> PersistentRuntimeResponse:
        runtime_key = self.build_assignment_runtime_key(assignment.id)
        existing = PersistentRuntimeRepository.get_by_runtime_key(db, runtime_key)
        if existing is not None:
            return PersistentRuntimeResponse.model_validate(existing)

        lifecycle_state = "running" if assignment.session_id else "sleeping"
        return PersistentRuntimeResponse(
            persistent_runtime_id=uuid.uuid4(),
            runtime_key=runtime_key,
            owner_type="agent_assignment",
            owner_id=assignment.id,
            agent_identity_id=assignment.agent_identity_id,
            assignment_id=assignment.id,
            session_id=assignment.session_id,
            container_id=assignment.container_id,
            lifecycle_state=lifecycle_state,
            auto_resume=True,
            idle_timeout_seconds=self.DEFAULT_ASSIGNMENT_IDLE_TIMEOUT_SECONDS,
            warm_retention_seconds=self.DEFAULT_ASSIGNMENT_WARM_RETENTION_SECONDS,
            keepalive_until=None,
            last_activity_at=assignment.last_triggered_at,
            last_started_at=assignment.last_triggered_at,
            last_stopped_at=None,
            last_stop_reason=None,
            worker_id=None,
            browser_enabled=False,
            filesystem_fingerprint=None,
            metadata_json=None,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )

    def list_controller_runtimes(
        self,
        db: Session,
        *,
        lifecycle_states: list[str] | None = None,
        limit: int | None = None,
    ) -> list[PersistentRuntimeControllerResponse]:
        runtimes = PersistentRuntimeRepository.list_by_lifecycle_states(
            db,
            lifecycle_states=lifecycle_states,
            limit=limit,
        )
        responses: list[PersistentRuntimeControllerResponse] = []
        now = self._now()
        for runtime in runtimes:
            has_live_work = (
                runtime.session_id is not None
                and self._session_has_live_work(db, runtime.session_id)
            )
            keepalive_active = (
                runtime.keepalive_until is not None and runtime.keepalive_until > now
            )
            payload = PersistentRuntimeResponse.model_validate(runtime).model_dump()
            responses.append(
                PersistentRuntimeControllerResponse(
                    **payload,
                    has_live_work=has_live_work,
                    keepalive_active=keepalive_active,
                )
            )
        return responses

    def ensure_server_agent_runtime(
        self,
        db: Session,
        *,
        agent_identity: AgentIdentity,
    ) -> PersistentRuntime:
        runtime_key = self.build_server_agent_runtime_key(agent_identity.id)
        existing = PersistentRuntimeRepository.get_by_runtime_key(db, runtime_key)
        if existing is not None:
            return existing

        runtime = PersistentRuntimeRepository.create(
            db,
            PersistentRuntime(
                runtime_key=runtime_key,
                owner_type="server_agent",
                owner_id=agent_identity.id,
                agent_identity_id=agent_identity.id,
                assignment_id=None,
                session_id=None,
                container_id=None,
                lifecycle_state="sleeping",
                auto_resume=True,
                idle_timeout_seconds=self.DEFAULT_SERVER_AGENT_IDLE_TIMEOUT_SECONDS,
                warm_retention_seconds=self.DEFAULT_SERVER_AGENT_WARM_RETENTION_SECONDS,
                browser_enabled=False,
            ),
        )
        db.flush()
        self._sync_legacy_owner_state(
            db,
            runtime,
            channel_task_id=None,
        )
        return runtime

    def ensure_assignment_runtime(
        self,
        db: Session,
        *,
        assignment: AgentAssignment,
    ) -> PersistentRuntime:
        runtime_key = self.build_assignment_runtime_key(assignment.id)
        existing = PersistentRuntimeRepository.get_by_runtime_key(db, runtime_key)
        if existing is not None:
            existing.assignment_id = assignment.id
            existing.session_id = assignment.session_id
            existing.container_id = assignment.container_id
            return existing

        runtime = PersistentRuntimeRepository.create(
            db,
            PersistentRuntime(
                runtime_key=runtime_key,
                owner_type="agent_assignment",
                owner_id=assignment.id,
                agent_identity_id=assignment.agent_identity_id,
                assignment_id=assignment.id,
                session_id=assignment.session_id,
                container_id=assignment.container_id,
                lifecycle_state="sleeping",
                auto_resume=True,
                idle_timeout_seconds=self.DEFAULT_ASSIGNMENT_IDLE_TIMEOUT_SECONDS,
                warm_retention_seconds=self.DEFAULT_ASSIGNMENT_WARM_RETENTION_SECONDS,
                browser_enabled=False,
            ),
        )
        db.flush()
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def reserve_runtime(
        self,
        db: Session,
        *,
        runtime_key: str,
        session_id: uuid.UUID,
        channel_task_id: uuid.UUID | None,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        if (
            runtime.session_id is not None
            and runtime.session_id != session_id
            and runtime.lifecycle_state == "running"
            and self._session_has_live_work(db, runtime.session_id)
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Persistent runtime is busy",
            )

        runtime.session_id = session_id
        runtime.lifecycle_state = "running"
        runtime.last_activity_at = self._now()
        runtime.last_stop_reason = None
        self._sync_legacy_owner_state(
            db,
            runtime,
            channel_task_id=channel_task_id,
        )
        return runtime

    def mark_running(
        self,
        db: Session,
        *,
        runtime_key: str,
        session_id: uuid.UUID | None = None,
        container_id: str | None = None,
        worker_id: str | None = None,
        browser_enabled: bool | None = None,
        filesystem_fingerprint: str | None = None,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.lifecycle_state = "running"
        runtime.last_activity_at = self._now()
        runtime.last_started_at = self._now()
        runtime.last_stop_reason = None
        if session_id is not None:
            runtime.session_id = session_id
        if container_id is not None:
            runtime.container_id = container_id
        if worker_id is not None:
            runtime.worker_id = worker_id
        if browser_enabled is not None:
            runtime.browser_enabled = browser_enabled
        if filesystem_fingerprint is not None:
            runtime.filesystem_fingerprint = filesystem_fingerprint
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def mark_sleeping(
        self,
        db: Session,
        *,
        runtime_key: str,
        stop_reason: str,
        worker_id: str | None = None,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.lifecycle_state = "sleeping"
        runtime.container_id = None
        runtime.last_stopped_at = self._now()
        runtime.last_stop_reason = stop_reason
        if worker_id is not None:
            runtime.worker_id = worker_id
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def mark_stale(
        self,
        db: Session,
        *,
        runtime_key: str,
        stop_reason: str = "container_missing",
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.lifecycle_state = "stale"
        runtime.container_id = None
        runtime.last_stopped_at = self._now()
        runtime.last_stop_reason = stop_reason
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def mark_manually_stopped(
        self,
        db: Session,
        *,
        runtime_key: str,
        stop_reason: str = "manual_stop",
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.lifecycle_state = "manually_stopped"
        runtime.container_id = None
        runtime.keepalive_until = None
        runtime.last_stopped_at = self._now()
        runtime.last_stop_reason = stop_reason
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def mark_removed(
        self,
        db: Session,
        *,
        runtime_key: str,
        stop_reason: str = "removed",
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.lifecycle_state = "removed"
        runtime.auto_resume = False
        runtime.container_id = None
        runtime.keepalive_until = None
        runtime.last_stopped_at = self._now()
        runtime.last_stop_reason = stop_reason
        self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def record_activity(
        self,
        db: Session,
        *,
        runtime_key: str,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.last_activity_at = self._now()
        return runtime

    def release_runtime_for_session(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        callback_status: str,
    ) -> PersistentRuntime | None:
        runtime = PersistentRuntimeRepository.get_by_session_id(db, session_id)
        if runtime is None:
            return None

        runtime.last_activity_at = self._now()
        normalized = (callback_status or "").strip().lower()
        if self._session_has_live_work(db, session_id):
            runtime.lifecycle_state = "running"
            self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
            return runtime

        if normalized in {"completed", "failed", "cancelled", "canceled"}:
            runtime.lifecycle_state = "warm_idle"
            self._sync_legacy_owner_state(db, runtime, channel_task_id=None)
        return runtime

    def extend_keepalive(
        self,
        db: Session,
        *,
        runtime_key: str,
        duration_seconds: int,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        bounded = max(0, min(int(duration_seconds), self.MAX_KEEPALIVE_SECONDS))
        if bounded == 0:
            runtime.keepalive_until = None
            return runtime
        runtime.keepalive_until = self._now() + timedelta(seconds=bounded)
        return runtime

    def clear_keepalive(
        self,
        db: Session,
        *,
        runtime_key: str,
    ) -> PersistentRuntime:
        runtime = self.get_by_runtime_key(db, runtime_key)
        runtime.keepalive_until = None
        return runtime

    def _sync_legacy_owner_state(
        self,
        db: Session,
        runtime: PersistentRuntime,
        *,
        channel_task_id: uuid.UUID | None,
    ) -> None:
        if runtime.agent_identity_id is not None:
            state = AgentPersistentStateRepository.get_by_agent_identity_id(
                db,
                runtime.agent_identity_id,
            )
            if state is not None:
                if runtime.lifecycle_state == "running":
                    state.runtime_status = "busy"
                    state.active_session_id = runtime.session_id
                    if channel_task_id is not None:
                        state.active_task_id = channel_task_id
                else:
                    state.runtime_status = "idle"
                    state.active_session_id = None
                    state.active_task_id = None
                state.last_synced_at = self._now()
                state.last_written_at = self._now()

        if runtime.assignment_id is not None:
            assignment = AgentAssignmentRepository.get_by_id(db, runtime.assignment_id)
            if assignment is not None:
                assignment.session_id = runtime.session_id
                assignment.container_id = runtime.container_id
