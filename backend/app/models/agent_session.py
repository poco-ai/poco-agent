from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_message import AgentMessage
    from app.models.agent_run import AgentRun
    from app.models.project import Project
    from app.models.session_queue_item import AgentSessionQueueItem
    from app.models.tool_execution import ToolExecution
    from app.models.usage_log import UsageLog
    from app.models.user_input_request import UserInputRequest


class AgentSession(Base, TimestampMixin):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index(
            "ix_agent_sessions_user_id_is_deleted_created_at",
            "user_id",
            "is_deleted",
            "created_at",
        ),
        Index(
            "ix_agent_sessions_sdk_session_id_is_deleted",
            "sdk_session_id",
            "is_deleted",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sdk_session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    workspace_archive_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_patch: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    workspace_files_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspace_manifest_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspace_archive_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspace_export_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    pinned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kind: Mapped[str] = mapped_column(
        String(50),
        default="chat",
        server_default=text("'chat'"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    project: Mapped[Optional["Project"]] = relationship(back_populates="sessions")
    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    queue_items: Mapped[list["AgentSessionQueueItem"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    user_input_requests: Mapped[list["UserInputRequest"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    @property
    def queued_query_count(self) -> int:
        return sum(
            1 for item in self.queue_items if item.status in {"queued", "paused"}
        )

    @property
    def next_queued_query_preview(self) -> str | None:
        queued_items = sorted(
            (item for item in self.queue_items if item.status in {"queued", "paused"}),
            key=lambda item: (item.sequence_no, item.created_at),
        )
        if not queued_items:
            return None
        return queued_items[0].prompt[:200]
