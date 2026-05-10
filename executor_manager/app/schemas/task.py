from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.filesystem import LocalMountConfig, FilesystemMode


class InputFile(BaseModel):
    """User-provided input file or URL attachment."""

    id: str | None = None
    type: Literal["file", "url"] = "file"
    name: str
    source: str
    size: int | None = None
    content_type: str | None = None
    path: str | None = None


AgentModel = Literal["sonnet", "opus", "haiku", "inherit"]


class SubAgentConfig(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    prompt: str | None = None
    model: AgentModel | None = None
    tools: list[str] | None = None


class TaskConfig(BaseModel):
    """Task configuration."""

    preset_id: int | None = None
    repo_url: str | None = None
    git_branch: str = "main"
    git_token_env_key: str | None = None
    model: str | None = None
    model_provider_id: str | None = None
    # Built-in browser capability toggle (Playwright MCP is injected internally by the executor).
    browser_enabled: bool = False
    # Built-in memory capability toggle (Memory MCP is injected internally by the executor).
    memory_enabled: bool = False
    mcp_config: dict = Field(default_factory=dict)
    skill_config: dict = Field(default_factory=dict)
    plugin_config: dict = Field(default_factory=dict)
    mcp_overrides: dict[str, bool] = Field(default_factory=dict)
    skill_overrides: dict[str, bool] = Field(default_factory=dict)
    plugin_overrides: dict[str, bool] = Field(default_factory=dict)
    mcp_server_ids: list[int] = Field(default_factory=list)
    skill_files: dict = Field(default_factory=dict)
    skill_ids: list[int] = Field(default_factory=list)
    plugin_files: dict = Field(default_factory=dict)
    plugin_ids: list[int] = Field(default_factory=list)
    subagent_ids: list[int] = Field(default_factory=list)
    subagent_configs: list[SubAgentConfig] = Field(default_factory=list)
    filesystem_mode: FilesystemMode = "sandbox"
    local_mounts: list[LocalMountConfig] = Field(default_factory=list)
    input_files: list[InputFile] = Field(default_factory=list)
    user_id: str = ""
    container_mode: Literal["ephemeral", "persistent"] = "ephemeral"
    container_id: str | None = None
    agent_identity_id: UUID | None = None
    channel_task_id: UUID | None = None
    agent_runtime_mode: Literal["persistent", "temporary"] | None = None
    server_id: UUID | None = None
    channel_id: UUID | None = None
    trigger_message_id: UUID | None = None
    thread_root_message_id: UUID | None = None
    trigger_type: str | None = None
    trigger_context: dict[str, Any] | None = None


class TaskCreateRequest(BaseModel):
    """Create task request."""

    prompt: str
    config: TaskConfig
    user_id: str
    session_id: str | None = None
    scheduled_at: datetime | None = None


class TaskCreateResponse(BaseModel):
    """Create task response."""

    task_id: str
    session_id: str
    status: str
    container_id: str | None = None


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    status: str
    next_run_time: str | None = None


class SessionStatusResponse(BaseModel):
    """Session status response."""

    session_id: str
    user_id: str
    sdk_session_id: str | None = None
    config_snapshot: dict | None = None
    workspace_archive_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class TaskCancelRequest(BaseModel):
    """Cancel task request."""

    session_id: str
    reason: str | None = "User canceled"


class TaskCancelResult(BaseModel):
    """Executor stop result for a session cancellation."""

    session_id: str
    stop_status: Literal["stopped", "not_found", "failed"]
    matched_container_count: int = 0
    stopped_container_count: int = 0
    message: str | None = None


class ContainerDeleteRequest(BaseModel):
    """Delete container request."""

    container_id: str
    reason: str | None = "Task completed"


class ContainerStatsResponse(BaseModel):
    """Container statistics response."""

    total_active: int
    persistent_containers: int
    ephemeral_containers: int
    containers: list[dict]
