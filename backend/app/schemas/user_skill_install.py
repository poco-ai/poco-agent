from datetime import datetime

from pydantic import BaseModel


class UserSkillInstallCreateRequest(BaseModel):
    skill_id: int
    enabled: bool = True


class UserSkillInstallUpdateRequest(BaseModel):
    enabled: bool | None = None


class UserSkillInstallResponse(BaseModel):
    id: int
    user_id: str
    skill_id: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
