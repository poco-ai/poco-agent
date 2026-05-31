from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InternalPersistentRuntimeListRequest(BaseModel):
    lifecycle_states: list[str] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=500)


class InternalPersistentRuntimeStartedRequest(BaseModel):
    session_id: UUID | None = None
    container_id: str | None = None
    worker_id: str | None = None
    browser_enabled: bool | None = None
    filesystem_fingerprint: str | None = None


class InternalPersistentRuntimeStoppedRequest(BaseModel):
    stop_reason: str = Field(min_length=1, max_length=255)
    worker_id: str | None = None


class InternalPersistentRuntimeActivityRequest(BaseModel):
    observed_at: datetime | None = None
