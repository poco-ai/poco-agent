from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceMemberResponse(BaseModel):
    membership_id: int = Field(validation_alias="id")
    workspace_id: UUID
    user_id: str
    role: str
    joined_at: datetime
    invited_by: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
