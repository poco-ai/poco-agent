import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent_session import AgentSession
    from app.models.project_file import ProjectFile
    from app.models.project_preset import ProjectPreset


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    project_presets: Mapped[list["ProjectPreset"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
