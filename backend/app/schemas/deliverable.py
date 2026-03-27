from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeliverableResponse(BaseModel):
    """Deliverable response schema."""

    id: UUID
    session_id: UUID
    kind: str
    logical_name: str
    latest_version_id: UUID | None = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DeliverableVersionResponse(BaseModel):
    """Deliverable version response schema."""

    id: UUID
    session_id: UUID
    run_id: UUID
    deliverable_id: UUID
    source_message_id: int | None = None
    version_no: int
    file_path: str
    file_name: str | None = None
    mime_type: str | None = None
    input_refs_json: dict[str, Any] | None = None
    related_tool_execution_ids_json: dict[str, Any] | None = None
    detection_metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
