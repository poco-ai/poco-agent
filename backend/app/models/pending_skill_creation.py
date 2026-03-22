import uuid

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class PendingSkillCreation(Base, TimestampMixin):
    __tablename__ = "pending_skill_creations"
    __table_args__ = (
        Index(
            "ix_pending_skill_creations_user_id_status_created_at",
            "user_id",
            "status",
            "created_at",
        ),
        UniqueConstraint(
            "session_id",
            "skill_relative_path",
            name="uq_pending_skill_creations_session_skill_path",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_use_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    detected_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resolved_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    workspace_files_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_relative_path: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
    )
    skill_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
