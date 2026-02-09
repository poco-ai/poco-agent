from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.watched_session import WatchedSession


class WatchRepository:
    @staticmethod
    def add_watch(db: Session, *, channel_id: int, session_id: str) -> WatchedSession:
        entry = WatchedSession(channel_id=channel_id, session_id=session_id)
        db.add(entry)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = WatchRepository.get_watch(
                db, channel_id=channel_id, session_id=session_id
            )
            if existing:
                return existing
            raise
        db.refresh(entry)
        return entry

    @staticmethod
    def remove_watch(db: Session, *, channel_id: int, session_id: str) -> int:
        stmt = (
            delete(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .where(WatchedSession.session_id == session_id)
        )
        result = db.connection().execute(stmt)
        db.commit()
        return int(result.rowcount or 0)

    @staticmethod
    def get_watch(
        db: Session, *, channel_id: int, session_id: str
    ) -> WatchedSession | None:
        stmt = (
            select(WatchedSession)
            .where(WatchedSession.channel_id == channel_id)
            .where(WatchedSession.session_id == session_id)
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def list_by_session(db: Session, *, session_id: str) -> list[WatchedSession]:
        stmt = select(WatchedSession).where(WatchedSession.session_id == session_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_by_channel(db: Session, *, channel_id: int) -> list[WatchedSession]:
        stmt = select(WatchedSession).where(WatchedSession.channel_id == channel_id)
        return list(db.execute(stmt).scalars().all())
