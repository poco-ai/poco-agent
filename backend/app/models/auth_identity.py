from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuthIdentity(Base, TimestampMixin):
    __tablename__ = "auth_identities"
    __table_args__ = (
        Index(
            "ix_auth_identities_provider_provider_user_id",
            "provider",
            "provider_user_id",
            unique=True,
        ),
        Index(
            "ix_auth_identities_user_id_provider",
            "user_id",
            "provider",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="identities")
