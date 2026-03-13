from datetime import datetime

from pydantic import BaseModel


class McpServerCreateRequest(BaseModel):
    name: str
    description: str | None = None
    server_config: dict
    scope: str | None = None


class McpServerUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    server_config: dict | None = None
    scope: str | None = None


class McpServerResponse(BaseModel):
    id: int
    name: str
    description: str | None
    server_config: dict
    scope: str
    owner_user_id: str | None
    created_at: datetime
    updated_at: datetime
