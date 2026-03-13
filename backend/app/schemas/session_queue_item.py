from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.input_file import InputFile


class SessionQueueItemResponse(BaseModel):
    """Persisted queued query response."""

    queue_item_id: UUID = Field(validation_alias="id")
    session_id: UUID
    sequence_no: int
    status: str
    prompt: str
    permission_mode: str
    attachments: list[InputFile] = Field(default_factory=list)
    client_request_id: str | None = None
    linked_run_id: UUID | None = None
    linked_user_message_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SessionQueueItemUpdateRequest(BaseModel):
    """Queued query update request."""

    prompt: str | None = None
    attachments: list[InputFile] | None = None
