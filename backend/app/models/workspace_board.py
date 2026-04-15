import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.workspace_issue import WorkspaceIssue


class WorkspaceBoard(Base, TimestampMixin):
    __tablename__ = "workspace_boards"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    issues: Mapped[list["WorkspaceIssue"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
    )
