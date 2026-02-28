from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.input_file import InputFile


class InputFileWithUrl(InputFile):
    """InputFile with an optional presigned URL for preview/download."""

    url: str | None = None


class MessageResponse(BaseModel):
    """Message response."""

    id: int
    role: str
    content: dict[str, Any]
    text_preview: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageWithFilesResponse(MessageResponse):
    """Message response including user-uploaded attachments.

    This schema is intentionally additive to keep backward compatibility with the existing MessageResponse.
    """

    attachments: list[InputFileWithUrl] | None = None


class MessageAttachmentsResponse(BaseModel):
    """Attachment payload for a specific message."""

    message_id: int
    attachments: list[InputFileWithUrl]
