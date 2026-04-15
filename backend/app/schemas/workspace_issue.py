from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

IssueStatus = Literal["todo", "in_progress", "done", "canceled"]
IssueType = Literal["task", "bug", "idea"]
IssuePriority = Literal["low", "medium", "high", "urgent"]


class WorkspaceIssueCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: IssueStatus = "todo"
    type: IssueType = "task"
    priority: IssuePriority = "medium"
    due_date: datetime | None = None
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None

    @model_validator(mode="after")
    def normalize_assignee(self) -> "WorkspaceIssueCreateRequest":
        if self.assignee_preset_id is not None:
            self.assignee_user_id = None
        return self


class WorkspaceIssueUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: IssueStatus | None = None
    type: IssueType | None = None
    priority: IssuePriority | None = None
    due_date: datetime | None = None
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None

    @model_validator(mode="after")
    def normalize_assignee(self) -> "WorkspaceIssueUpdateRequest":
        if self.assignee_preset_id is not None:
            self.assignee_user_id = None
        return self


class WorkspaceIssueResponse(BaseModel):
    issue_id: UUID = Field(validation_alias="id")
    workspace_id: UUID
    board_id: UUID
    title: str
    description: str | None = None
    status: str
    type: str
    priority: str
    due_date: datetime | None = None
    assignee_user_id: str | None = None
    assignee_preset_id: int | None = None
    reporter_user_id: str | None = None
    related_project_id: UUID | None = None
    creator_user_id: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
