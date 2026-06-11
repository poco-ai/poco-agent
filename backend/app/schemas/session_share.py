from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.message import MessageResponse
from app.schemas.callback import FileChange
from app.schemas.server_channel_message import (
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.workspace import FileNode

TimelineItemType = Literal["message", "run", "channel_message", "channel_event"]


class SessionShareCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class SharedSessionSummary(BaseModel):
    session_id: UUID
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class SharedToolExecution(BaseModel):
    id: UUID
    run_id: UUID | None = None
    message_id: int | None = None
    tool_use_id: str | None = None
    tool_name: str
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    is_error: bool = False
    duration_ms: int | None = None
    browser_screenshot_url: str | None = None
    created_at: datetime
    updated_at: datetime


class SharedRunSummary(BaseModel):
    run_id: UUID
    user_message_id: int
    status: str
    progress: int
    schedule_mode: str
    workspace_export_status: str | None = None
    replay_step_count: int = 0
    file_change_count: int = 0
    file_changes: list[FileChange] = Field(default_factory=list)
    workspace_files: list[FileNode] = Field(default_factory=list)
    tool_executions: list[SharedToolExecution] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConversationTimelineItem(BaseModel):
    id: str
    item_type: TimelineItemType
    label: str
    status: str | None = None
    role: str | None = None
    message_id: int | None = None
    run_id: UUID | None = None
    channel_message_id: UUID | None = None
    source_message_id: int | None = None
    source_run_id: UUID | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionShareResponse(BaseModel):
    share_id: UUID = Field(validation_alias="id")
    source_session_id: UUID
    token: str
    title: str | None = None
    description: str | None = None
    is_revoked: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SessionSharePublicResponse(BaseModel):
    share_id: UUID = Field(validation_alias="id")
    title: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SessionShareSnapshotResponse(BaseModel):
    share: SessionSharePublicResponse
    session: SharedSessionSummary
    messages: list[MessageResponse]
    runs: list[SharedRunSummary]
    timeline: list[ConversationTimelineItem]


class SessionShareForkResponse(BaseModel):
    session_id: UUID
    source_session_id: UUID
    share_id: UUID


class SessionShareToChannelRequest(BaseModel):
    server_id: UUID
    channel_id: UUID
    title: str | None = Field(default=None, max_length=255)


class SessionShareToChannelResponse(BaseModel):
    share_id: UUID
    source_session_id: UUID
    event: ServerChannelMessageResponse
    thread: ServerChannelThreadResponse
    timeline: list[ConversationTimelineItem]
