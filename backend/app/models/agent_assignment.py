import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class AgentAssignment(Base, TimestampMixin):
    __tablename__ = "agent_assignments"
    __table_args__ = (
        UniqueConstraint("issue_id", name="uq_agent_assignments_issue_id"),
        Index("ix_agent_assignments_workspace_status", "workspace_id", "status"),
        Index("ix_agent_assignments_trigger_mode_status", "trigger_mode", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preset_id: Mapped[int] = mapped_column(
        ForeignKey("presets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
