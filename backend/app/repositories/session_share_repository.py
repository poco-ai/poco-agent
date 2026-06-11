import uuid

from sqlalchemy.orm import Session

from app.models.session_share import SessionShare


class SessionShareRepository:
    @staticmethod
    def create(session_db: Session, share: SessionShare) -> SessionShare:
        session_db.add(share)
        return share

    @staticmethod
    def get_by_token(session_db: Session, token: str) -> SessionShare | None:
        return (
            session_db.query(SessionShare).filter(SessionShare.token == token).first()
        )

    @staticmethod
    def get_active_by_token(session_db: Session, token: str) -> SessionShare | None:
        return (
            session_db.query(SessionShare)
            .filter(
                SessionShare.token == token,
                SessionShare.is_revoked.is_(False),
            )
            .first()
        )

    @staticmethod
    def list_by_source_session(
        session_db: Session,
        source_session_id: uuid.UUID,
    ) -> list[SessionShare]:
        return (
            session_db.query(SessionShare)
            .filter(
                SessionShare.source_session_id == source_session_id,
                SessionShare.is_revoked.is_(False),
            )
            .order_by(SessionShare.created_at.desc())
            .all()
        )
