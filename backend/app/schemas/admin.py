from typing import Literal

from pydantic import BaseModel


class ModelConfigAdminUpdateRequest(BaseModel):
    default_model: str
    model_list: list[str]


class SystemRoleUpdateRequest(BaseModel):
    system_role: Literal["user", "admin"]


class ClaudeMdAdminUpsertRequest(BaseModel):
    enabled: bool = True
    content: str = ""
