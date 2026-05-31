from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PersistentRuntimeResponse(BaseModel):
    persistent_runtime_id: UUID = Field(
        validation_alias=AliasChoices("id", "persistent_runtime_id")
    )
    runtime_key: str
    owner_type: str
    owner_id: UUID
    agent_identity_id: UUID | None = None
    assignment_id: UUID | None = None
    session_id: UUID | None = None
    container_id: str | None = None
    lifecycle_state: str
    auto_resume: bool
    idle_timeout_seconds: int
    warm_retention_seconds: int
    keepalive_until: datetime | None = None
    last_activity_at: datetime | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    last_stop_reason: str | None = None
    worker_id: str | None = None
    browser_enabled: bool = False
    filesystem_fingerprint: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PersistentRuntimeControllerResponse(PersistentRuntimeResponse):
    has_live_work: bool = False
    keepalive_active: bool = False


class PersistentRuntimeKeepaliveRequest(BaseModel):
    duration_seconds: int = Field(ge=0, le=86400)
