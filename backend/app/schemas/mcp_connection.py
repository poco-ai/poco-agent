from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class McpConnectionResponse(BaseModel):
    id: UUID
    run_id: UUID
    session_id: UUID
    server_id: int | None = None
    server_name: str
    state: str
    attempt_count: int
    last_error: str | None = None
    connection_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
