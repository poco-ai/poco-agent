from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.sub_agent import SubAgentModel


class PresetSubAgentConfig(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    prompt: str | None = None
    model: SubAgentModel | None = None
    tools: list[str] | None = None


class PresetVisualSummary(BaseModel):
    key: str
    url: str | None = None
    version: str | None = None
    name: str | None = None


class PresetBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    visual_key: str = Field(min_length=1, max_length=255)
    prompt_template: str | None = None
    browser_enabled: bool = False
    memory_enabled: bool = False
    skill_ids: list[int] = Field(default_factory=list)
    mcp_server_ids: list[int] = Field(default_factory=list)
    plugin_ids: list[int] = Field(default_factory=list)
    subagent_configs: list[PresetSubAgentConfig] = Field(default_factory=list)


class PresetCreateRequest(PresetBase):
    pass


class PresetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    visual_key: str | None = Field(default=None, min_length=1, max_length=255)
    prompt_template: str | None = None
    browser_enabled: bool | None = None
    memory_enabled: bool | None = None
    skill_ids: list[int] | None = None
    mcp_server_ids: list[int] | None = None
    plugin_ids: list[int] | None = None
    subagent_configs: list[PresetSubAgentConfig] | None = None


class PresetResponse(BaseModel):
    preset_id: int = Field(validation_alias="id")
    user_id: str
    name: str
    description: str | None = None
    visual_key: str
    visual_url: str | None = None
    visual_version: str | None = None
    visual_name: str | None = None
    prompt_template: str | None = None
    browser_enabled: bool
    memory_enabled: bool
    skill_ids: list[int]
    mcp_server_ids: list[int]
    plugin_ids: list[int]
    subagent_configs: list[PresetSubAgentConfig]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PresetAdminResponse(PresetResponse):
    pass
