import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_message import AgentMessage
    from app.models.agent_scheduled_task import AgentScheduledTask
    from app.models.agent_session import AgentSession
    from app.models.usage_log import UsageLog


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("agent_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False, index=True
    )
    permission_mode: Mapped[str] = mapped_column(
        String(50), default="default", nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    schedule_mode: Mapped[str] = mapped_column(
        String(50), default="immediate", nullable=False, index=True
    )
    scheduled_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_scheduled_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    config_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    claimed_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped["AgentSession"] = relationship(back_populates="runs")
    user_message: Mapped["AgentMessage"] = relationship(foreign_keys=[user_message_id])
    scheduled_task: Mapped[Optional["AgentScheduledTask"]] = relationship(
        back_populates="runs"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
