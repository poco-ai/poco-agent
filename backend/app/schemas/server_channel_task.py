from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

TaskStatus = Literal["todo", "in_progress", "in_review", "done"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
TASK_STATUS_VALUES: tuple[str, ...] = ("todo", "in_progress", "in_review", "done")


class ServerChannelTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = "todo"
    position: int | None = Field(default=None, ge=0)
    priority: TaskPriority | None = "medium"
    due_date: datetime | None = None
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None
    source_message_id: UUID | None = None

    @model_validator(mode="after")
    def normalize_assignee(self) -> "ServerChannelTaskCreateRequest":
        if self.assignee_preset_id is not None:
            self.assignee_user_id = None
        return self


class ServerChannelTaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None


class ServerChannelTaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    position: int = Field(default=0, ge=0)


class ServerChannelTaskClaimRequest(BaseModel):
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None

    @model_validator(mode="after")
    def normalize_assignee(self) -> "ServerChannelTaskClaimRequest":
        if self.assignee_preset_id is not None:
            self.assignee_user_id = None
        return self


class ServerChannelTaskResponse(BaseModel):
    task_id: UUID = Field(validation_alias=AliasChoices("id", "task_id"))
    server_id: UUID
    channel_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    position: int
    priority: str | None = None
    due_date: datetime | None = None
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None
    creator_user_id: str
    updated_by: str | None = None
    thread_root_message_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
