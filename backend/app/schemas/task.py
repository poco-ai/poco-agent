from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.session import TaskConfig


class TaskEnqueueRequest(BaseModel):
    """Enqueue a new agent run (task)."""

    prompt: str
    config: TaskConfig | None = None
    session_id: UUID | None = None
    project_id: UUID | None = None
    permission_mode: str = "default"
    schedule_mode: str = "immediate"
    timezone: str | None = None
    scheduled_at: datetime | None = None
    client_request_id: str | None = None


class TaskEnqueueResponse(BaseModel):
    """Enqueue task response."""

    session_id: UUID
    accepted_type: Literal["run", "queued_query"] = "run"
    run_id: UUID | None = None
    queue_item_id: UUID | None = None
    status: str
    queued_query_count: int = 0


class InternalTaskEnqueueRequest(BaseModel):
    """Internal task enqueue request carrying an already-resolved config snapshot."""

    prompt: str
    config_snapshot: dict | None = None
    session_id: UUID | None = None
    permission_mode: str = "default"
    schedule_mode: str = "immediate"
    timezone: str | None = None
    scheduled_at: datetime | None = None
    client_request_id: str | None = None


class InternalTaskStatusResponse(BaseModel):
    """Internal unified task status for either a run or a queued query."""

    task_id: UUID
    task_type: Literal["run", "queued_query"]
    session_id: UUID
    status: str
    run_id: UUID | None = None
    queue_item_id: UUID | None = None
