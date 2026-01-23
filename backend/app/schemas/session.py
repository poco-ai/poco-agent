from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.callback import AgentCurrentState
from app.schemas.input_file import InputFile


class TaskConfig(BaseModel):
    """Task configuration."""

    repo_url: str | None = None
    git_branch: str = "main"
    # MCP server enable/disable toggles (true=enabled, false=disabled).
    # Servers not in this dict use their default enabled state from user installations.
    mcp_config: dict[str, bool] = Field(default_factory=dict)
    # Skill enable/disable toggles (true=enabled, false=disabled).
    # Skills not in this dict use their default enabled state from user installations.
    skill_config: dict[str, bool] = Field(default_factory=dict)
    input_files: list[InputFile] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    """Request to create a session."""

    config: TaskConfig | None = None
    project_id: UUID | None = None


class SessionUpdateRequest(BaseModel):
    """Request to update a session."""

    status: str | None = None
    sdk_session_id: str | None = None
    workspace_archive_url: str | None = None
    project_id: UUID | None = None
    state_patch: dict[str, Any] | None = None
    workspace_files_prefix: str | None = None
    workspace_manifest_key: str | None = None
    workspace_archive_key: str | None = None
    workspace_export_status: str | None = None


class SessionResponse(BaseModel):
    """Session response."""

    session_id: UUID = Field(validation_alias="id")
    user_id: str
    project_id: UUID | None
    sdk_session_id: str | None
    title: str | None = None
    config_snapshot: dict[str, Any] | None
    workspace_archive_url: str | None
    state_patch: AgentCurrentState | None = None
    workspace_export_status: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SessionStateResponse(BaseModel):
    """Session state response."""

    session_id: UUID = Field(validation_alias="id")
    status: str
    state_patch: AgentCurrentState | None = None
    workspace_export_status: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
