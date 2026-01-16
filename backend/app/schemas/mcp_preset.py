from datetime import datetime

from pydantic import BaseModel


class McpPresetCreateRequest(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    category: str | None = None
    transport: str
    default_config: dict | None = None
    config_schema: dict | None = None
    version: str | None = None


class McpPresetUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    transport: str | None = None
    default_config: dict | None = None
    config_schema: dict | None = None
    version: str | None = None
    is_active: bool | None = None


class McpPresetResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str | None
    category: str | None
    transport: str
    default_config: dict | None
    config_schema: dict | None
    source: str
    owner_user_id: str | None
    version: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
