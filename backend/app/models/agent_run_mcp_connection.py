import uuid

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class AgentRunMcpConnection(Base, TimestampMixin):
    __tablename__ = "agent_run_mcp_connections"
    __table_args__ = (
        Index(
            "ix_agent_run_mcp_connections_run_id_server_name",
            "run_id",
            "server_name",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    server_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    connection_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
