import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class PermissionAuditEvent(Base, TimestampMixin):
    __tablename__ = "permission_audit_events"
    __table_args__ = (
        Index("ix_permission_audit_events_run_id", "run_id"),
        Index("ix_permission_audit_events_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_input: Mapped[dict[str, Any] | None] = mapped_column(
        "tool_input", JSON, nullable=True
    )
    policy_action: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_reason: Mapped[str | None] = mapped_column(nullable=True)
    audit_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
