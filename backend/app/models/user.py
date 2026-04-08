import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth_identity import AuthIdentity
    from app.models.user_session import UserSession


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    primary_email: Mapped[str | None] = mapped_column(
        String(320), nullable=True, unique=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default=text("'active'"),
        nullable=False,
    )

    identities: Mapped[list["AuthIdentity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())
