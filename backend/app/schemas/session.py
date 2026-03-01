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
    # Optional env var key holding a GitHub token (e.g. "GITHUB_TOKEN").
    git_token_env_key: str | None = None
    # Optional explicit model override for this session/run.
    model: str | None = None
    # Built-in browser capability toggle (Playwright MCP is injected internally by the executor).
    browser_enabled: bool = False
    # MCP server enable/disable toggles (true=enabled, false=disabled).
    # Servers not in this dict use their default enabled state from user installations.
    mcp_config: dict[str, bool] = Field(default_factory=dict)
    # Skill enable/disable toggles (true=enabled, false=disabled).
    # Skills not in this dict use their default enabled state from user installations.
    skill_config: dict[str, bool] = Field(default_factory=dict)
    # Plugin enable/disable toggles (true=enabled, false=disabled).
    # Plugins not in this dict use their default enabled state from user installations.
    plugin_config: dict[str, bool] = Field(default_factory=dict)
    # Optional explicit subagent selection (by id). When omitted, backend resolves
    # enabled subagents as defaults.
    subagent_ids: list[int] = Field(default_factory=list)
    input_files: list[InputFile] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    """Request to create a session."""

    config: TaskConfig | None = None
    project_id: UUID | None = None


class SessionUpdateRequest(BaseModel):
    """Request to update a session."""

    status: str | None = None
    sdk_session_id: str | None = None
    title: str | None = None
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


class SessionCancelRequest(BaseModel):
    """Request to cancel a session (cancel all unfinished runs)."""

    reason: str | None = None


class SessionCancelResponse(BaseModel):
    """Session cancel response."""

    session_id: UUID
    status: str
    canceled_runs: int = 0
    expired_user_input_requests: int = 0
    executor_cancelled: bool = False


class SessionBranchRequest(BaseModel):
    """Request to branch a session from a message checkpoint."""

    message_id: int = Field(gt=0)


class SessionRegenerateRequest(BaseModel):
    """Request to regenerate an assistant message within the same session."""

    user_message_id: int = Field(gt=0)
    assistant_message_id: int = Field(gt=0)


class SessionEditMessageRequest(BaseModel):
    """Request to edit a user message then regenerate from that point."""

    user_message_id: int = Field(gt=0)
    content: str = Field(min_length=1)


class SessionBranchResponse(BaseModel):
    """Session branch response."""

    session_id: UUID
    source_session_id: UUID
    cutoff_message_id: int
