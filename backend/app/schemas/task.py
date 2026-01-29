from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.session import TaskConfig


class TaskEnqueueRequest(BaseModel):
    """Enqueue a new agent run (task)."""

    prompt: str
    config: TaskConfig | None = None
    session_id: UUID | None = None
    project_id: UUID | None = None
    # Claude Code permission mode for this run (stored on agent_runs).
    # "plan" enables planning-only mode until ExitPlanMode is approved.
    permission_mode: str = "default"
    schedule_mode: str = "immediate"
    timezone: str | None = None
    scheduled_at: datetime | None = None


class TaskEnqueueResponse(BaseModel):
    """Enqueue task response."""

    session_id: UUID
    run_id: UUID
    status: str
