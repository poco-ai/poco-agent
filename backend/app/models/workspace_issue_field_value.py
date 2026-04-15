import uuid

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class WorkspaceIssueFieldValue(Base, TimestampMixin):
    __tablename__ = "workspace_issue_field_values"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_board_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
