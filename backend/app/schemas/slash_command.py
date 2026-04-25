from datetime import datetime
from typing import Literal

from pydantic import BaseModel


SlashCommandMode = Literal["raw", "structured"]


class SlashCommandCreateRequest(BaseModel):
    name: str
    enabled: bool = True
    mode: SlashCommandMode = "raw"

    # Optional display fields (used by structured mode rendering and UI list view).
    description: str | None = None
    argument_hint: str | None = None
    allowed_tools: str | None = None

    # mode="structured"
    content: str | None = None
    # mode="raw"
    raw_markdown: str | None = None


class SlashCommandUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    mode: SlashCommandMode | None = None

    description: str | None = None
    argument_hint: str | None = None
    allowed_tools: str | None = None

    content: str | None = None
    raw_markdown: str | None = None


class SlashCommandResponse(BaseModel):
    id: int
    user_id: str
    name: str
    enabled: bool
    mode: SlashCommandMode
    description: str | None = None
    argument_hint: str | None = None
    allowed_tools: str | None = None
    content: str | None = None
    raw_markdown: str | None = None
    created_at: datetime
    updated_at: datetime


class SlashCommandAdminResponse(BaseModel):
    id: int
    user_id: str
    name: str
    enabled: bool
    mode: SlashCommandMode
    description: str | None = None
    argument_hint: str | None = None
    allowed_tools: str | None = None
    content: str | None = None
    raw_markdown: str | None = None
    created_at: datetime
    updated_at: datetime
