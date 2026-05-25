import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class ChannelArtifact(Base, TimestampMixin):
    __tablename__ = "channel_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "source_session_id",
            "logical_path",
            name="uq_channel_artifacts_session_logical_path",
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
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("server_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    publisher_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="workspace_export",
        server_default=text("'workspace_export'"),
    )
    logical_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_previewable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
