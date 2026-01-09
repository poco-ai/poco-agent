from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.enums import FileStatus, TodoStatus


class TodoItem(BaseModel):
    """A todo item tracking a task."""

    content: str
    status: TodoStatus
    active_form: str | None = None


class McpStatus(BaseModel):
    """Status of an MCP server connection."""

    name: str
    status: str


class FileChange(BaseModel):
    """Detailed information about a single file change."""

    path: str
    status: FileStatus
    added_lines: int = 0
    deleted_lines: int = 0
    diff: str | None = None
    old_path: str | None = None


class WorkspaceState(BaseModel):
    """Current state of the workspace including file changes."""

    repository: str | None = None
    branch: str | None = None
    total_added_lines: int = 0
    total_deleted_lines: int = 0
    file_changes: list[FileChange] = Field(default_factory=list)
    last_change: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCurrentState(BaseModel):
    """Current execution state of the agent."""

    todos: list[TodoItem] = Field(default_factory=list)
    mcp_status: list[McpStatus] = Field(default_factory=list)
    workspace_state: WorkspaceState | None = None
    current_step: str | None = None
