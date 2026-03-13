import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_message import AgentMessage
    from app.models.agent_run import AgentRun
    from app.models.agent_session import AgentSession


class AgentSessionQueueItem(Base, TimestampMixin):
    __tablename__ = "agent_session_queue_items"
    __table_args__ = (
        Index(
            "ix_agent_session_queue_items_session_id_status_sequence_no",
            "session_id",
            "status",
            "sequence_no",
        ),
        UniqueConstraint(
            "session_id",
            "sequence_no",
            name="uq_agent_session_queue_items_session_id_sequence_no",
        ),
        UniqueConstraint(
            "session_id",
            "client_request_id",
            name="uq_agent_session_queue_items_session_id_client_request_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="queued",
        server_default=text("'queued'"),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    permission_mode: Mapped[str] = mapped_column(
        String(50),
        default="default",
        server_default=text("'default'"),
        nullable=False,
    )
    run_config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    client_request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    linked_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_user_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    session: Mapped["AgentSession"] = relationship(back_populates="queue_items")
    linked_run: Mapped["AgentRun | None"] = relationship(foreign_keys=[linked_run_id])
    linked_user_message: Mapped["AgentMessage | None"] = relationship(
        foreign_keys=[linked_user_message_id]
    )

    @property
    def attachments(self) -> list[dict[str, Any]]:
        snapshot = self.run_config_snapshot
        if not isinstance(snapshot, dict):
            return []
        input_files = snapshot.get("input_files")
        return list(input_files) if isinstance(input_files, list) else []
