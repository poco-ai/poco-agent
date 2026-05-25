from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChannelArtifactResponse(BaseModel):
    artifact_id: UUID = Field(validation_alias="id")
    server_id: UUID
    channel_id: UUID
    source_session_id: UUID | None = None
    agent_identity_id: UUID | None = None
    publisher_user_id: str | None = None
    source_kind: str
    logical_path: str
    display_name: str
    object_key: str
    mime_type: str | None = None
    size_bytes: int | None = None
    is_previewable: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChannelArtifactPublisherSummary(BaseModel):
    actor_type: Literal["user", "agent"]
    user_id: str | None = None
    agent_identity_id: UUID | None = None
    agent_handle: str | None = None
    label: str
    avatar_url: str | None = None
    visual_key: str | None = None


class ChannelArtifactCandidateResponse(BaseModel):
    artifact_id: UUID = Field(validation_alias="id")
    display_name: str
    logical_path: str
    mime_type: str | None = None
    size_bytes: int | None = None
    source_kind: str
    published_by_user_id: str | None = Field(
        default=None,
        validation_alias="publisher_user_id",
    )
    published_by_agent_identity_id: UUID | None = Field(
        default=None,
        validation_alias="agent_identity_id",
    )
    publisher: ChannelArtifactPublisherSummary | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AgentChannelArtifactMetadata(BaseModel):
    artifact_id: UUID
    logical_path: str
    display_name: str
    source_kind: str
    source_session_id: UUID | None = None
    agent_identity_id: UUID | None = None
    publisher_user_id: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    is_previewable: bool
    content_kind: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentChannelArtifactListResponse(BaseModel):
    artifacts: list[AgentChannelArtifactMetadata]


class AgentChannelArtifactReadRequest(BaseModel):
    artifact_id: UUID | None = None
    logical_path: str | None = None
    max_bytes: int | None = Field(default=None, ge=1, le=65536)


class AgentChannelArtifactReadResponse(BaseModel):
    artifact: AgentChannelArtifactMetadata
    content: str | None = None
    truncated: bool = False
    metadata_only: bool = False
    reason: str | None = None


class AgentChannelArtifactSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    limit: int = Field(default=10, ge=1, le=50)
    include_content: bool = False


class AgentChannelArtifactSearchResponse(BaseModel):
    artifacts: list[AgentChannelArtifactMetadata]
