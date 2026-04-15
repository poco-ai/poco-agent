from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


BoardFieldType = Literal["text", "number", "date", "select", "multi_select"]


class WorkspaceBoardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkspaceBoardResponse(BaseModel):
    board_id: UUID = Field(validation_alias="id")
    workspace_id: UUID
    name: str
    description: str | None = None
    created_by: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkspaceBoardFieldCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    field_type: BoardFieldType
    options: list[str] = Field(default_factory=list)
    sort_order: int = 0
    description: str | None = None
