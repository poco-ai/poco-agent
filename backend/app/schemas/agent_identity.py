from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.persistent_runtime import PersistentRuntimeResponse


class AgentPersistentStateResponse(BaseModel):
    persistent_state_id: UUID = Field(
        validation_alias=AliasChoices("id", "persistent_state_id")
    )
    agent_identity_id: UUID
    state_root_path: str
    profile_path: str
    memory_path: str
    notes_dir_path: str
    state_dir_path: str
    artifacts_dir_path: str
    state_version: int
    runtime_status: str
    active_task_id: UUID | None = None
    active_session_id: UUID | None = None
    last_synced_at: datetime | None = None
    last_written_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentIdentityCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    handle: str | None = Field(default=None, max_length=255)
    description: str | None = None
    preset_id: int = Field(gt=0)
    visual_key: str | None = Field(default=None, max_length=100)
    visibility: str = Field(default="server", max_length=50)


class AgentIdentityUpdateRequest(BaseModel):
    description: str | None = None


class AgentRuntimePinRequest(BaseModel):
    duration_hours: int = Field(ge=1, le=24)


class AgentIdentityResponse(BaseModel):
    agent_identity_id: UUID = Field(
        validation_alias=AliasChoices("id", "agent_identity_id")
    )
    server_id: UUID
    preset_id: int
    handle: str
    display_name: str
    description: str | None = None
    visual_key: str
    visibility: str
    lifecycle_state: str
    created_by: str
    updated_by: str | None = None
    removed_at: datetime | None = None
    removed_by: str | None = None
    persistent_state: AgentPersistentStateResponse | None = None
    runtime_summary: PersistentRuntimeResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChannelAgentMemberCreateRequest(BaseModel):
    agent_identity_id: UUID
    role: str = Field(default="member", max_length=50)


class ChannelAgentMemberResponse(BaseModel):
    membership_id: int = Field(validation_alias=AliasChoices("id", "membership_id"))
    channel_id: UUID
    agent_identity_id: UUID
    role: str
    joined_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
