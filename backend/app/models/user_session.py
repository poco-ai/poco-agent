import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index(
            "ix_user_sessions_user_id_revoked_at_expires_at",
            "user_id",
            "revoked_at",
            "expires_at",
        ),
        Index(
            "ix_user_sessions_session_token_hash",
            "session_token_hash",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())
