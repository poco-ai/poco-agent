from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None = Field(default=None, validation_alias="primary_email")
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
