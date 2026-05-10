from pydantic import BaseModel, Field


class PluginConfigResolveRequest(BaseModel):
    """Request to resolve plugins for execution."""

    plugin_ids: list[int] = Field(default_factory=list)
    plugin_overrides: dict[str, bool] | None = None
