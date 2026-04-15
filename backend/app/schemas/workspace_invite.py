from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.workspace_member import WorkspaceRole


class WorkspaceInviteCreateRequest(BaseModel):
    role: WorkspaceRole = Field(default="member")
    expires_in_days: int = Field(default=7, ge=1, le=30)
    max_uses: int = Field(default=1, ge=1, le=100)


class WorkspaceInviteAcceptRequest(BaseModel):
    token: str


class WorkspaceInviteRevokeRequest(BaseModel):
    pass


class WorkspaceInviteResponse(BaseModel):
    invite_id: UUID = Field(validation_alias="id")
    workspace_id: UUID
    token: str
    role: WorkspaceRole
    expires_at: datetime
    created_by: str
    max_uses: int
    used_count: int
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
