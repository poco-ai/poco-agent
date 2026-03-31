from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectFileAddRequest(BaseModel):
    file_name: str = Field(min_length=1)
    file_source: str = Field(min_length=1)
    file_size: int | None = Field(default=None, ge=0)
    file_content_type: str | None = None


class ProjectFileResponse(BaseModel):
    project_file_id: int = Field(validation_alias="id")
    project_id: UUID
    file_name: str
    file_source: str
    file_size: int | None = None
    file_content_type: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
