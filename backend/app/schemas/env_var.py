from datetime import datetime

from pydantic import BaseModel


class EnvVarCreateRequest(BaseModel):
    key: str
    value: str
    is_secret: bool = True
    description: str | None = None
    scope: str = "global"


class EnvVarUpdateRequest(BaseModel):
    value: str | None = None
    is_secret: bool | None = None
    description: str | None = None
    scope: str | None = None


class EnvVarResponse(BaseModel):
    id: int
    user_id: str
    key: str
    value: str | None
    is_secret: bool
    description: str | None
    scope: str
    created_at: datetime
    updated_at: datetime
