from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass(slots=True)
class InboundMessage:
    provider: str
    destination: str
    message_id: str
    text: str
    sender_id: str | None = None
    send_address: str | None = None
    raw: dict[str, Any] | None = None


class SessionSnapshot(BaseModel):
    id: str
    title: str | None = None
    status: str


class RunSnapshot(BaseModel):
    id: str | None = None
    status: str | None = None
    progress: int | None = None
    error_message: str | None = None


class EventStateSnapshot(BaseModel):
    callback_status: str | None = None
    current_step: str | None = None
    todos_total: int = 0
    todos_completed: int = 0


class MessageSnapshot(BaseModel):
    id: int
    role: str
    text: str
    text_preview: str | None = None


class UserInputRequestSnapshot(BaseModel):
    id: str
    tool_name: str
    tool_input: dict = Field(default_factory=dict)
    status: str
    expires_at: datetime
    answered_at: datetime | None = None


class ImBackendEvent(BaseModel):
    id: str
    type: str
    version: int = 1
    occurred_at: datetime
    user_id: str
    session: SessionSnapshot
    run: RunSnapshot | None = None
    state: EventStateSnapshot | None = None
    message: MessageSnapshot | None = None
    user_input_request: UserInputRequestSnapshot | None = None
