from datetime import datetime

from pydantic import BaseModel

from app.schemas.source import SourceInfo


class SkillCreateRequest(BaseModel):
    name: str
    entry: dict
    description: str | None = None
    scope: str | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    entry: dict | None = None
    description: str | None = None
    scope: str | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class SkillResponse(BaseModel):
    id: int
    name: str
    description: str | None
    entry: dict
    source: SourceInfo
    scope: str
    owner_user_id: str | None
    default_enabled: bool
    force_enabled: bool
    created_at: datetime
    updated_at: datetime
