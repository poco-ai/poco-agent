from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionGroupResponse,
)
from app.schemas.agent_identity import AgentIdentityResponse
from app.schemas.user_profile import UserPublicProfileResponse

ServerChannelMessageType = Literal["user", "system", "task", "event"]


class ServerChannelMessageCreateRequest(BaseModel):
    content: dict[str, Any]
    text_preview: str | None = None
    message_type: ServerChannelMessageType = "user"
    thread_root_message_id: UUID | None = None


class ServerChannelMessageResponse(BaseModel):
    message_id: UUID = Field(validation_alias=AliasChoices("id", "message_id"))
    channel_id: UUID
    author_user_id: str | None
    author_user: UserPublicProfileResponse | None = None
    author_agent: AgentIdentityResponse | None = None
    message_type: ServerChannelMessageType
    content: dict[str, Any]
    text_preview: str | None = None
    thread_root_message_id: UUID | None = None
    reply_count: int = 0
    reactions: list[ServerChannelMessageReactionGroupResponse] = Field(
        default_factory=list
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ServerChannelThreadResponse(BaseModel):
    root: ServerChannelMessageResponse
    replies: list[ServerChannelMessageResponse]
