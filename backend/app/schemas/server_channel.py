from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.user_profile import UserPublicProfileResponse

ServerChannelVisibility = Literal["public", "private"]
ServerConversationType = Literal["channel", "direct_message"]
ServerSystemChannelType = Literal["personal", "public"]


class ServerChannelCreateRequest(BaseModel):
    name: str
    description: str | None = None
    visibility: ServerChannelVisibility = "public"
    member_user_ids: list[str] = Field(default_factory=list)
    agent_identity_ids: list[UUID] = Field(default_factory=list)


class ServerChannelUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class ServerChannelMemberAddRequest(BaseModel):
    user_id: str
    role: str = "member"


class DirectMessageCreateRequest(BaseModel):
    target_user_id: str | None = None
    target_agent_identity_id: UUID | None = None


class ServerChannelResponse(BaseModel):
    channel_id: UUID = Field(validation_alias=AliasChoices("id", "channel_id"))
    server_id: UUID
    name: str
    slug: str
    description: str | None = None
    conversation_type: ServerConversationType
    visibility: ServerChannelVisibility
    system_channel_type: ServerSystemChannelType | None = None
    is_system_channel: bool = False
    direct_user_id: str | None = None
    direct_agent_identity_id: UUID | None = None
    created_by: str | None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ServerChannelMemberResponse(BaseModel):
    membership_id: int = Field(validation_alias=AliasChoices("id", "membership_id"))
    channel_id: UUID
    user_id: str
    user: UserPublicProfileResponse | None = None
    role: str
    joined_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
