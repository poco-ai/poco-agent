import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace_board import WorkspaceBoard


class WorkspaceIssue(Base, TimestampMixin):
    __tablename__ = "workspace_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="todo",
        server_default=text("'todo'"),
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="task",
        server_default=text("'task'"),
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="medium",
        server_default=text("'medium'"),
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    assignee_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    board: Mapped["WorkspaceBoard"] = relationship(back_populates="issues")
