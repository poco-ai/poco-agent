from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SubAgentMode = Literal["raw", "structured"]
SubAgentModel = Literal["sonnet", "opus", "haiku", "inherit"]


class SubAgentCreateRequest(BaseModel):
    name: str
    enabled: bool = True
    mode: SubAgentMode = "structured"

    # mode="structured"
    description: str | None = None
    prompt: str | None = None
    tools: list[str] | None = None
    model: SubAgentModel | None = None

    # mode="raw"
    raw_markdown: str | None = None


class SubAgentUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    mode: SubAgentMode | None = None

    description: str | None = None
    prompt: str | None = None
    tools: list[str] | None = None
    model: SubAgentModel | None = None

    raw_markdown: str | None = None


class SubAgentResponse(BaseModel):
    id: int
    user_id: str
    name: str
    enabled: bool
    mode: SubAgentMode

    description: str | None = None
    prompt: str | None = None
    tools: list[str] | None = None
    model: SubAgentModel | None = None
    raw_markdown: str | None = None

    created_at: datetime
    updated_at: datetime


class SubAgentAdminResponse(SubAgentResponse):
    pass


class SubAgentResolveRequest(BaseModel):
    subagent_ids: list[int] | None = None


class SubAgentDefinition(BaseModel):
    description: str
    prompt: str
    tools: list[str] | None = None
    model: SubAgentModel | None = None


class SubAgentResolveResponse(BaseModel):
    structured_agents: dict[str, SubAgentDefinition] = Field(default_factory=dict)
    raw_agents: dict[str, str] = Field(default_factory=dict)
