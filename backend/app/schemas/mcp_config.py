from pydantic import BaseModel, Field


class McpConfigResolveRequest(BaseModel):
    """Request to resolve MCP server configs for execution."""

    server_ids: list[int] = Field(default_factory=list)
    server_overrides: dict[str, bool] | None = None
