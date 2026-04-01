from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.usage import UsageResponse


class RunStatus(str, Enum):
    """Run status enum."""

    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class RunResponse(BaseModel):
    """Run response."""

    run_id: UUID = Field(validation_alias="id")
    session_id: UUID
    user_message_id: int
    status: str
    permission_mode: str
    progress: int
    schedule_mode: str
    scheduled_task_id: UUID | None = None
    scheduled_at: datetime
    config_snapshot: dict | None = None
    config_layers: dict | None = None
    resolved_hook_specs: list[dict] | None = None
    permission_policy_snapshot: dict | None = None
    claimed_by: str | None
    lease_expires_at: datetime | None
    attempts: int
    last_error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    usage: UsageResponse | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator(
        "config_snapshot",
        "config_layers",
        "permission_policy_snapshot",
        mode="before",
    )
    @classmethod
    def _normalize_optional_dict(cls, value: object) -> dict | None:
        return value if isinstance(value, dict) else None

    @field_validator("resolved_hook_specs", mode="before")
    @classmethod
    def _normalize_optional_list(cls, value: object) -> list[dict] | None:
        if not isinstance(value, list):
            return None
        return [item for item in value if isinstance(item, dict)]


class RunClaimRequest(BaseModel):
    """Claim next run request."""

    worker_id: str
    lease_seconds: int = 30
    schedule_modes: list[str] | None = None


class RunClaimResponse(BaseModel):
    """Claim next run response for worker dispatch."""

    run: RunResponse
    user_id: str
    prompt: str
    config_snapshot: dict | None = None
    sdk_session_id: str | None = None


class RunStartRequest(BaseModel):
    """Mark run as running request."""

    worker_id: str


class RunFailRequest(BaseModel):
    """Mark run as failed request."""

    worker_id: str
    error_message: str | None = None
