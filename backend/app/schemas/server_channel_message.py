from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionGroupResponse,
)
from app.schemas.agent_identity import AgentIdentityResponse
from app.schemas.user_profile import UserPublicProfileResponse

ServerChannelMessageType = Literal["user", "system", "task", "event"]
ServerChannelMessageEntityKind = Literal[
    "agent",
    "user",
    "artifact",
    "task",
    "message",
    "thread",
]
ServerChannelMessageEntityAction = Literal["trigger", "mention", "reference"]


class ServerChannelMessageEntityRange(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class ServerChannelMessageEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: ServerChannelMessageEntityKind
    action: ServerChannelMessageEntityAction
    target_id: str = Field(validation_alias=AliasChoices("target_id", "targetId"))
    display_text: str = Field(
        validation_alias=AliasChoices("display_text", "displayText")
    )
    inserted_text: str = Field(
        validation_alias=AliasChoices("inserted_text", "insertedText")
    )
    range: ServerChannelMessageEntityRange | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


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


class ServerChannelMessageContextResponse(BaseModel):
    target: ServerChannelMessageResponse
    messages: list[ServerChannelMessageResponse]
