import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class AgentRunMcpConnectionEvent(Base, TimestampMixin):
    __tablename__ = "agent_run_mcp_connection_events"
    __table_args__ = (
        Index(
            "ix_mcp_connection_events_connection_id",
            "connection_id",
        ),
        Index("ix_mcp_connection_events_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_run_mcp_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    event_source: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
