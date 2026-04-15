import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_session import AgentSession
    from app.models.preset import Preset
    from app.models.project_file import ProjectFile
    from app.models.project_local_mount import ProjectLocalMount


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
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
    forked_from_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_preset_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Default git repository context for this project (GitHub-only in v1).
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Store env var key (e.g. "GITHUB_TOKEN"), not the secret itself.
    git_token_env_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    sessions: Mapped[list["AgentSession"]] = relationship(back_populates="project")
    project_files: Mapped[list["ProjectFile"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    project_local_mounts: Mapped[list["ProjectLocalMount"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectLocalMount.sort_order",
    )
    default_preset: Mapped["Preset | None"] = relationship(
        back_populates="default_projects",
        foreign_keys=[default_preset_id],
    )
