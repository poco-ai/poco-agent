from datetime import datetime

from pydantic import BaseModel


class UserSkillInstallCreateRequest(BaseModel):
    preset_id: int
    enabled: bool = True
    overrides: dict | None = None


class UserSkillInstallUpdateRequest(BaseModel):
    enabled: bool | None = None
    overrides: dict | None = None


class UserSkillInstallResponse(BaseModel):
    id: int
    user_id: str
    preset_id: int
    enabled: bool
    overrides: dict | None
    created_at: datetime
    updated_at: datetime
