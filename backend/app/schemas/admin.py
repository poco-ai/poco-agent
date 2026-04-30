from typing import Literal

from pydantic import BaseModel, Field


class ModelConfigAdminUpdateRequest(BaseModel):
    default_model: str
    model_list: list[str]


class SystemRoleUpdateRequest(BaseModel):
    system_role: Literal["user", "admin"]


class ClaudeMdAdminUpsertRequest(BaseModel):
    enabled: bool = True
    content: str = ""


class RuntimeEnvPolicyAdminUpdateRequest(BaseModel):
    mode: Literal["disabled", "opt_in"]
    allowlist_patterns: list[str] = Field(default_factory=list)
    denylist_patterns: list[str] = Field(default_factory=list)
