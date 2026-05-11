import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class ServerChannelTask(Base, TimestampMixin):
    __tablename__ = "server_channel_tasks"
    __table_args__ = (
        UniqueConstraint(
            "thread_root_message_id",
            name="uq_server_channel_tasks_thread_root_message_id",
        ),
        UniqueConstraint(
            "channel_id",
            "display_number",
            name="uq_server_channel_tasks_channel_display_number",
        ),
        CheckConstraint(
            """
            num_nonnulls(
                assignee_user_id,
                assignee_preset_id,
                assignee_agent_identity_id
            ) <= 1
            """,
            name="ck_server_channel_tasks_single_assignee",
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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    display_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="todo",
        server_default=text("'todo'"),
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assignee_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assignee_preset_id: Mapped[int | None] = mapped_column(
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assignee_agent_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_user_id: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    thread_root_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("server_channel_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
