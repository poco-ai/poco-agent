import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session, aliased

from app.models.agent_run import AgentRun


class RunRepository:
    """Data access layer for agent runs."""

    @staticmethod
    def create(
        session_db: Session,
        session_id: uuid.UUID,
        user_message_id: int,
        schedule_mode: str = "immediate",
        scheduled_at: datetime | None = None,
        config_snapshot: dict | None = None,
    ) -> AgentRun:
        """Creates a new run.

        Note: Does not commit. Transaction handled by Service layer.
        """
        run = AgentRun(
            session_id=session_id,
            user_message_id=user_message_id,
            status="queued",
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
        """Gets a run by ID."""
        return session_db.query(AgentRun).filter(AgentRun.id == run_id).first()

    @staticmethod
    def list_by_session(
        session_db: Session,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentRun]:
        """Lists runs for a session."""
        return (
            session_db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .order_by(AgentRun.scheduled_at.asc(), AgentRun.created_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def release_expired_claims(session_db: Session) -> int:
        """Release expired claimed runs back to queued.

        Returns:
            Number of released runs.
        """
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
        """Claims the next available run for execution.

        Uses SELECT ... FOR UPDATE SKIP LOCKED to support multiple workers.
        Ensures only one claimed/running run per session at a time.
        """
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

        stmt = (
            select(AgentRun)
            .where(AgentRun.status == "queued")
            .where(AgentRun.scheduled_at <= now)
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
