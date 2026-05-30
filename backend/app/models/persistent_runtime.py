import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class PersistentRuntime(Base, TimestampMixin):
    __tablename__ = "persistent_runtimes"
    __table_args__ = (
        Index("ix_persistent_runtimes_runtime_key", "runtime_key", unique=True),
        Index("ix_persistent_runtimes_owner", "owner_type", "owner_id"),
        Index(
            "ix_persistent_runtimes_lifecycle_state",
            "lifecycle_state",
        ),
        Index("ix_persistent_runtimes_container_id", "container_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    runtime_key: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    agent_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="sleeping",
        server_default=text("'sleeping'"),
    )
    auto_resume: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    idle_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=900,
        server_default=text("900"),
    )
    warm_retention_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=120,
        server_default=text("120"),
    )
    keepalive_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_stop_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    browser_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    filesystem_fingerprint: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
