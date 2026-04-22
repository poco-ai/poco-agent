from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CallbackStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TodoItem(BaseModel):
    content: str
    status: str
    active_form: str | None = None


class McpStatus(BaseModel):
    server_name: str
    status: str
    message: str | None = None


class FileChange(BaseModel):
    path: str
    status: str
    added_lines: int = 0
    deleted_lines: int = 0
    diff: str | None = None
    old_path: str | None = None


class WorkspaceState(BaseModel):
    repository: str | None = None
    branch: str | None = None
    total_added_lines: int = 0
    total_deleted_lines: int = 0
    file_change_count: int = 0
    file_changes: list[FileChange] = Field(default_factory=list)
    last_change: datetime


class BrowserState(BaseModel):
    enabled: bool = False


class AgentCurrentState(BaseModel):
    todos: list[TodoItem] = Field(default_factory=list)
    mcp_status: list[McpStatus] = Field(default_factory=list)
    browser: BrowserState | None = None
    workspace_state: WorkspaceState | None = None
    current_step: str | None = None


class AgentCallbackRequest(BaseModel):
    session_id: str
    run_id: str | None = None
    time: datetime
    status: CallbackStatus
    progress: int
    error_message: str | None = None
    new_message: Any | None = None
    state_patch: AgentCurrentState | None = None
    sdk_session_id: str | None = None
    workspace_files_prefix: str | None = None
    workspace_manifest_key: str | None = None
    workspace_archive_key: str | None = None
    workspace_export_status: str | None = None


class CallbackResponse(BaseModel):
    session_id: str
    status: str
    callback_status: CallbackStatus | None = None
    message: str | None = None
