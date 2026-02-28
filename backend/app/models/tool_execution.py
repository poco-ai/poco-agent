import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_message import AgentMessage
    from app.models.agent_session import AgentSession


class ToolExecution(Base, TimestampMixin):
    __tablename__ = "tool_executions"
    __table_args__ = (
        Index(
            "ix_tool_executions_session_id_updated_at_id",
            "session_id",
            "updated_at",
            "id",
        ),
        UniqueConstraint(
            "session_id",
            "tool_use_id",
            name="uq_tool_executions_session_tool_use_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="CASCADE"), nullable=False
    )
    tool_use_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="SET NULL"), nullable=True
    )
    is_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped["AgentSession"] = relationship(back_populates="tool_executions")
    message: Mapped["AgentMessage"] = relationship(
        back_populates="tool_executions",
        foreign_keys=[message_id],
    )
    result_message: Mapped["AgentMessage"] = relationship(
        foreign_keys=[result_message_id],
        back_populates="tool_result_executions",
    )
