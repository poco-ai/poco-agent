import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.deliverable import Deliverable


class DeliverableVersion(Base, TimestampMixin):
    """Represents a concrete generated file such as '报价单 v2.xlsx'."""

    __tablename__ = "deliverable_versions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "run_id",
            "file_path",
            name="uq_deliverable_versions_session_run_path",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deliverables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_refs_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    related_tool_execution_ids_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    detection_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    deliverable: Mapped["Deliverable"] = relationship(
        back_populates="versions",
        foreign_keys=[deliverable_id],
    )
