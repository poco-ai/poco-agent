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
