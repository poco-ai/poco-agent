from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None = Field(default=None, validation_alias="primary_email")
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuthProviderStatus(BaseModel):
    name: Literal["google", "github"]
    enabled: bool


class AuthConfigResponse(BaseModel):
    mode: Literal["oauth_required", "oauth_optional", "single_user"]
    login_required: bool
    single_user_effective: bool
    setup_required: bool
    configured_providers: list[Literal["google", "github"]]
    providers: list[AuthProviderStatus]
