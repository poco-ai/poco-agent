from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.filesystem import LocalMountConfig


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    default_model: str | None = None
    default_preset_id: int | None = Field(default=None, gt=0)
    local_mounts: list[LocalMountConfig] | None = None
    repo_url: str | None = None
    git_branch: str | None = None
    git_token_env_key: str | None = None
    scope: Literal["personal", "workspace"] = "personal"
    workspace_id: UUID | None = None
    access_policy: Literal[
        "private", "workspace_read", "workspace_write", "admins_only"
    ] = "private"


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    default_model: str | None = None
    default_preset_id: int | None = Field(default=None, gt=0)
    local_mounts: list[LocalMountConfig] | None = None
    repo_url: str | None = None
    git_branch: str | None = None
    git_token_env_key: str | None = None
    access_policy: Literal[
        "private", "workspace_read", "workspace_write", "admins_only"
    ] | None = None


class ProjectCopyRequest(BaseModel):
    target_scope: Literal["personal", "workspace"]
    workspace_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    access_policy: Literal[
        "private", "workspace_read", "workspace_write", "admins_only"
    ] | None = None


class ProjectResponse(BaseModel):
    project_id: UUID = Field(validation_alias="id")
    user_id: str
    scope: str = "personal"
    workspace_id: UUID | None = None
    owner_user_id: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    access_policy: str = "private"
    forked_from_project_id: UUID | None = None
    name: str
    description: str | None = None
    default_model: str | None = None
    default_preset_id: int | None = None
    local_mounts: list[LocalMountConfig] = Field(default_factory=list)
    repo_url: str | None = None
    git_branch: str | None = None
    git_token_env_key: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
