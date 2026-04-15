from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentAssignmentResponse(BaseModel):
    assignment_id: UUID = Field(validation_alias="id")
    workspace_id: UUID
    issue_id: UUID
    preset_id: int
    trigger_mode: Literal["persistent_sandbox", "scheduled_task"]
    session_id: UUID | None = None
    container_id: str | None = None
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    prompt: str
    schedule_cron: str | None = None
    last_triggered_at: datetime | None = None
    last_completed_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentAssignmentActionResponse(BaseModel):
    assignment: AgentAssignmentResponse
    issue_status: str


class AgentAssignmentDispatchRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)


class AgentAssignmentDispatchResponse(BaseModel):
    dispatched: int = 0
    assignment_ids: list[UUID] = Field(default_factory=list)
    skipped: int = 0
    errors: int = 0
