import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.server import Server
    from app.models.server_channel_member import ServerChannelMember


class ServerChannel(Base, TimestampMixin):
    __tablename__ = "server_channels"
    __table_args__ = (
        UniqueConstraint(
            "server_id",
            "slug",
            name="uq_server_channels_server_id_slug",
        ),
        Index(
            "uq_server_channels_server_system_channel_type",
            "server_id",
            "system_channel_type",
            unique=True,
            postgresql_where=text("system_channel_type IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="channel",
        server_default=text("'channel'"),
        index=True,
    )
    visibility: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    system_channel_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    direct_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    direct_agent_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    server: Mapped["Server"] = relationship(back_populates="channels")
    members: Mapped[list["ServerChannelMember"]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
    )
