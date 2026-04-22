from datetime import datetime

from pydantic import BaseModel


class McpServerCreateRequest(BaseModel):
    name: str
    description: str | None = None
    server_config: dict
    scope: str | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class McpServerUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    server_config: dict | None = None
    scope: str | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class McpServerResponse(BaseModel):
    id: int
    name: str
    description: str | None
    server_config: dict
    has_sensitive_data: bool = False
    scope: str
    owner_user_id: str | None
    default_enabled: bool
    force_enabled: bool
    created_at: datetime
    updated_at: datetime


class McpServerAdminResponse(BaseModel):
    id: int
    name: str
    description: str | None
    server_config: dict
    masked_server_config: dict
    has_sensitive_data: bool
    scope: str
    owner_user_id: str | None
    default_enabled: bool
    force_enabled: bool
    created_at: datetime
    updated_at: datetime
