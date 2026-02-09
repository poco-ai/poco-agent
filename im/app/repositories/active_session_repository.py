from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.active_session import ActiveSession


class ActiveSessionRepository:
    @staticmethod
    def get_by_channel(db: Session, *, channel_id: int) -> ActiveSession | None:
        stmt = select(ActiveSession).where(ActiveSession.channel_id == channel_id)
        return db.execute(stmt).scalars().first()

    @staticmethod
    def set_active(db: Session, *, channel_id: int, session_id: str) -> ActiveSession:
        existing = ActiveSessionRepository.get_by_channel(db, channel_id=channel_id)
        if existing:
            existing.session_id = session_id
            db.commit()
            db.refresh(existing)
            return existing

        entry = ActiveSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def clear(db: Session, *, channel_id: int) -> None:
        stmt = delete(ActiveSession).where(ActiveSession.channel_id == channel_id)
        db.execute(stmt)
        db.commit()

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[ActiveSession]:
        stmt = select(ActiveSession).where(ActiveSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())
