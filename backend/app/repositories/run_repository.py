import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession


class RunRepository:
    """Data access layer for agent runs."""

    UNFINISHED_STATUSES = ("queued", "claimed", "running")
    BLOCKING_STATUSES = ("claimed", "running")
    TERMINAL_STATUSES = ("completed", "failed", "canceled")

    @staticmethod
    def _blocking_priority():
        return case(
            (AgentRun.status == "running", 0),
            (AgentRun.status == "claimed", 1),
            else_=2,
        )

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        user_message_id: int,
        *,
        permission_mode: str = "default",
        schedule_mode: str = "immediate",
        scheduled_at: datetime | None = None,
        config_snapshot: dict | None = None,
    ) -> AgentRun:
        run = AgentRun(
            session_id=session_id,
            user_message_id=user_message_id,
            status="queued",
            permission_mode=permission_mode,
            progress=0,
            schedule_mode=schedule_mode,
            attempts=0,
            config_snapshot=config_snapshot,
        )
        if scheduled_at is not None:
            run.scheduled_at = scheduled_at
        session_db.add(run)
        return run

    @staticmethod
    def get_by_id(session_db: Session, run_id: uuid.UUID) -> AgentRun | None:
        return session_db.query(AgentRun).filter(AgentRun.id == run_id).first()

    @staticmethod
    def get_latest_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> AgentRun | None:
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .order_by(AgentRun.created_at.desc())
            .first()
        )

    @staticmethod
    def get_unfinished_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> AgentRun | None:
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(AgentRun.status.in_(RunRepository.UNFINISHED_STATUSES))
            .order_by(
                RunRepository._blocking_priority().asc(),
                AgentRun.scheduled_at.asc(),
                AgentRun.created_at.asc(),
            )
            .first()
        )

    @staticmethod
    def get_latest_terminal_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> AgentRun | None:
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(AgentRun.status.in_(RunRepository.TERMINAL_STATUSES))
            .order_by(AgentRun.finished_at.desc(), AgentRun.created_at.desc())
            .first()
        )

    @staticmethod
    def get_blocking_by_session(
        session_db: Session,
        session_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> AgentRun | None:
        current_time = now or datetime.now(timezone.utc)
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(
                or_(
                    AgentRun.status.in_(RunRepository.BLOCKING_STATUSES),
                    and_(
                        AgentRun.status == "queued",
                        AgentRun.scheduled_at <= current_time,
                    ),
                )
            )
            .order_by(
                RunRepository._blocking_priority().asc(),
                AgentRun.scheduled_at.asc(),
                AgentRun.created_at.asc(),
            )
            .first()
        )

    @staticmethod
    def get_latest_active_by_session(
        session_db: Session, session_id: uuid.UUID
    ) -> AgentRun | None:
        return RunRepository.get_blocking_by_session(session_db, session_id)

    @staticmethod
    def list_by_session(
        session_db: Session,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentRun]:
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .order_by(AgentRun.scheduled_at.asc(), AgentRun.created_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def list_by_session_and_user_message_ids(
        session_db: Session,
        session_id: uuid.UUID,
        user_message_ids: list[int],
    ) -> list[AgentRun]:
        if not user_message_ids:
            return []
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .filter(AgentRun.user_message_id.in_(user_message_ids))
            .order_by(AgentRun.created_at.asc())
            .all()
        )

    @staticmethod
    def list_by_scheduled_task(
        session_db: Session,
        scheduled_task_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentRun]:
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.scheduled_task_id == scheduled_task_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def release_expired_claims(session_db: Session) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(AgentRun)
            .where(AgentRun.status == "claimed")
            .where(AgentRun.lease_expires_at.is_not(None))
            .where(AgentRun.lease_expires_at < now)
            .values(status="queued", claimed_by=None, lease_expires_at=None)
        )
        result = session_db.connection().execute(stmt)
        return result.rowcount

    @staticmethod
    def claim_next(
        session_db: Session,
        worker_id: str,
        lease_seconds: int = 30,
        schedule_modes: list[str] | None = None,
    ) -> AgentRun | None:
        if lease_seconds <= 0:
            lease_seconds = 30

        _ = RunRepository.release_expired_claims(session_db)
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_seconds)

        running_or_claimed = aliased(AgentRun)
        has_active_run = exists(
            select(1)
            .select_from(running_or_claimed)
            .where(running_or_claimed.session_id == AgentRun.session_id)
            .where(running_or_claimed.status.in_(["claimed", "running"]))
        )
        has_live_session = exists(
            select(1)
            .select_from(AgentSession)
            .where(AgentSession.id == AgentRun.session_id)
            .where(AgentSession.is_deleted.is_(False))
        )

        stmt = (
            select(AgentRun)
            .where(AgentRun.status == "queued")
            .where(AgentRun.scheduled_at <= now)
            .where(has_live_session)
            .where(~has_active_run)
            .order_by(AgentRun.scheduled_at.asc(), AgentRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if schedule_modes:
            stmt = stmt.where(AgentRun.schedule_mode.in_(schedule_modes))

        run = session_db.execute(stmt).scalars().first()
        if not run:
            return None

        run.status = "claimed"
        run.claimed_by = worker_id
        run.lease_expires_at = lease_until
        return run
