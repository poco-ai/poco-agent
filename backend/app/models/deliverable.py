import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.deliverable_version import DeliverableVersion


class Deliverable(Base, TimestampMixin):
    """Represents a logical output object such as a quotation sheet, proposal, or presentation draft."""

    __tablename__ = "deliverables"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "kind",
            "logical_name",
            name="uq_deliverables_session_kind_name",
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
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    logical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("deliverable_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    versions: Mapped[list["DeliverableVersion"]] = relationship(
        back_populates="deliverable",
        foreign_keys="DeliverableVersion.deliverable_id",
    )
    latest_version: Mapped["DeliverableVersion | None"] = relationship(
        foreign_keys=[latest_version_id],
    )
