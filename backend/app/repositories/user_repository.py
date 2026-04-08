from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Data access layer for users."""

    @staticmethod
    def create(
        session_db: Session,
        *,
        user_id: str,
        primary_email: str | None,
        display_name: str | None,
        avatar_url: str | None,
        status: str = "active",
    ) -> User:
        user = User(
            id=user_id,
            primary_email=primary_email,
            display_name=display_name,
            avatar_url=avatar_url,
            status=status,
        )
        session_db.add(user)
        return user

    @staticmethod
    def get_by_id(session_db: Session, user_id: str) -> User | None:
        return session_db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(session_db: Session, email: str) -> User | None:
        return session_db.query(User).filter(User.primary_email == email).first()
