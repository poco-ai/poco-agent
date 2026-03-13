from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InputFile(BaseModel):
    """User-provided input file or URL attachment."""

    id: str | None = None
    type: Literal["file", "url"] = "file"
    name: str
    source: str
    size: int | None = None
    content_type: str | None = None
    path: str | None = None


class TaskConfig(BaseModel):
    """Task configuration."""

    repo_url: str | None = None
    git_branch: str = "main"
    # Built-in browser capability toggle (Playwright MCP is injected internally by the executor).
    browser_enabled: bool = False
    # Built-in memory capability toggle (Memory MCP is injected internally by the executor).
    memory_enabled: bool = False
    mcp_config: dict = Field(default_factory=dict)
    mcp_server_ids: list[int] = Field(default_factory=list)
    skill_files: dict = Field(default_factory=dict)
    skill_ids: list[int] = Field(default_factory=list)
    plugin_files: dict = Field(default_factory=dict)
    plugin_ids: list[int] = Field(default_factory=list)
    input_files: list[InputFile] = Field(default_factory=list)
    user_id: str = ""
    container_mode: Literal["ephemeral", "persistent"] = "ephemeral"
    container_id: str | None = None


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
