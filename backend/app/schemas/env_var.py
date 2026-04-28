from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EnvVarScope = Literal["system", "user"]


class EnvVarCreateRequest(BaseModel):
    key: str
    value: str
    description: str | None = None


class EnvVarUpdateRequest(BaseModel):
    value: str | None = None
    description: str | None = None


class EnvVarPublicResponse(BaseModel):
    id: int
    user_id: str
    key: str
    description: str | None
    scope: EnvVarScope
    is_set: bool
    created_at: datetime
    updated_at: datetime


# Internal-only schemas (protected by INTERNAL_API_TOKEN)


class SystemEnvVarCreateRequest(BaseModel):
    key: str
    value: str = ""
    description: str | None = None


class SystemEnvVarUpdateRequest(BaseModel):
    value: str | None = None
    description: str | None = None


class SystemEnvVarResponse(BaseModel):
    id: int
    user_id: str
    key: str
    value: str
    description: str | None
    scope: EnvVarScope
    created_at: datetime
    updated_at: datetime


class SystemEnvVarAdminResponse(BaseModel):
    id: int
    user_id: str
    key: str
    description: str | None
    scope: EnvVarScope
    is_set: bool
    masked_value: str
    created_at: datetime
    updated_at: datetime
