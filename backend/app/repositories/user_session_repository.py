from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.user_session import UserSession


class UserSessionRepository:
    """Data access layer for user sessions."""

    @staticmethod
    def create(
        session_db: Session,
        *,
        session_id: str,
        user_id: str,
        session_token_hash: str,
        expires_at: datetime,
        ip_address: str | None,
        user_agent: str | None,
    ) -> UserSession:
        user_session = UserSession(
            id=session_id,
            user_id=user_id,
            session_token_hash=session_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session_db.add(user_session)
        return user_session

    @staticmethod
    def get_active_by_token_hash(
        session_db: Session,
        session_token_hash: str,
        now: datetime,
    ) -> UserSession | None:
        return (
            session_db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(
                UserSession.session_token_hash == session_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .first()
        )

    @staticmethod
    def revoke_by_token_hash(
        session_db: Session,
        session_token_hash: str,
        revoked_at: datetime,
    ) -> int:
        return (
            session_db.query(UserSession)
            .filter(
                UserSession.session_token_hash == session_token_hash,
                UserSession.revoked_at.is_(None),
            )
            .update(
                {
                    UserSession.revoked_at: revoked_at,
                    UserSession.last_seen_at: revoked_at,
                },
                synchronize_session=False,
            )
        )
