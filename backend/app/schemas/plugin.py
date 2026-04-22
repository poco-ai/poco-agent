from datetime import datetime

from pydantic import BaseModel

from app.schemas.source import SourceInfo


class PluginCreateRequest(BaseModel):
    name: str
    entry: dict
    scope: str | None = None
    description: str | None = None
    version: str | None = None
    manifest: dict | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class PluginUpdateRequest(BaseModel):
    name: str | None = None
    entry: dict | None = None
    scope: str | None = None
    description: str | None = None
    version: str | None = None
    manifest: dict | None = None
    default_enabled: bool | None = None
    force_enabled: bool | None = None


class PluginResponse(BaseModel):
    id: int
    name: str
    entry: dict
    source: SourceInfo
    scope: str
    owner_user_id: str | None
    default_enabled: bool
    force_enabled: bool
    description: str | None = None
    version: str | None = None
    manifest: dict | None = None
    created_at: datetime
    updated_at: datetime


class PluginAdminResponse(BaseModel):
    id: int
    name: str
    masked_entry: dict
    masked_manifest: dict | None = None
    entry_has_sensitive_data: bool
    manifest_has_sensitive_data: bool
    source: SourceInfo
    scope: str
    owner_user_id: str | None
    default_enabled: bool
    force_enabled: bool
    description: str | None = None
    version: str | None = None
    created_at: datetime
    updated_at: datetime
