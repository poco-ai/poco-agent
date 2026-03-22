import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PendingSkillCreationResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    tool_use_id: str | None = None
    detected_name: str
    resolved_name: str | None
    description: str | None
    workspace_files_prefix: str | None
    skill_relative_path: str
    status: str
    skill_id: int | None
    error: str | None
    result: dict | None = None
    created_at: datetime
    updated_at: datetime


class PendingSkillCreationConfirmRequest(BaseModel):
    resolved_name: str | None = None
    description: str | None = Field(default=None, max_length=1000)
    overwrite: bool = False


class PendingSkillCreationCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
