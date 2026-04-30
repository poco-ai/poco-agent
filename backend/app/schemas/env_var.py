from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EnvVarScope = Literal["system", "user"]
RuntimeVisibility = Literal["none", "admins_only", "all_users"]


class EnvVarCreateRequest(BaseModel):
    key: str
    value: str
    description: str | None = None
    expose_to_runtime: bool = False


class EnvVarUpdateRequest(BaseModel):
    value: str | None = None
    description: str | None = None
    expose_to_runtime: bool | None = None


class EnvVarPublicResponse(BaseModel):
    id: int
    user_id: str
    key: str
    description: str | None
    scope: EnvVarScope
    is_set: bool
    expose_to_runtime: bool
    created_at: datetime
    updated_at: datetime


# Internal-only schemas (protected by INTERNAL_API_TOKEN)


class SystemEnvVarCreateRequest(BaseModel):
    key: str
    value: str = ""
    description: str | None = None
    runtime_visibility: RuntimeVisibility = "none"


class SystemEnvVarUpdateRequest(BaseModel):
    value: str | None = None
    description: str | None = None
    runtime_visibility: RuntimeVisibility | None = None


class SystemEnvVarResponse(BaseModel):
    id: int
    user_id: str
    key: str
    value: str
    description: str | None
    scope: EnvVarScope
    runtime_visibility: RuntimeVisibility
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
    runtime_visibility: RuntimeVisibility
    created_at: datetime
    updated_at: datetime
