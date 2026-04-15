import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Preset(Base, TimestampMixin):
    __tablename__ = "presets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "is_deleted", name="uq_preset_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="personal",
        server_default=text("'personal'"),
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_policy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="private",
        server_default=text("'private'"),
    )
    forked_from_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="preset-visual-01",
        server_default=text("'preset-visual-01'"),
    )

    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    memory_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    skill_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    mcp_server_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    plugin_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    subagent_configs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    default_projects: Mapped[list["Project"]] = relationship(
        back_populates="default_preset",
        foreign_keys="Project.default_preset_id",
    )
