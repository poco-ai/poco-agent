from typing import Literal

from pydantic import BaseModel, Field


class InputFile(BaseModel):
    """User-provided input file or URL attachment."""

    id: str | None = None
    type: Literal["file", "url"] = "file"
    name: str
    source: str
    size: int | None = None
    content_type: str | None = None
    path: str | None = None


AgentModel = Literal["sonnet", "opus", "haiku", "inherit"]


class AgentDefinition(BaseModel):
    """Claude Agent SDK subagent definition (programmatic mode)."""

    description: str
    prompt: str
    tools: list[str] | None = None
    model: AgentModel | None = None


class TaskConfig(BaseModel):
    repo_url: str | None = None
    git_branch: str = "main"
    # Optional env var key holding a GitHub token (non-secret; used by manager).
    git_token_env_key: str | None = None
    # Resolved GitHub token (secret) injected by Executor Manager at runtime.
    git_token: str | None = None
    # Built-in browser capability toggle (Playwright MCP is injected internally by the executor).
    browser_enabled: bool = False
    mcp_config: dict = Field(default_factory=dict)
    mcp_server_ids: list[int] = Field(default_factory=list)
    skill_files: dict = Field(default_factory=dict)
    skill_ids: list[int] = Field(default_factory=list)
    agents: dict[str, AgentDefinition] = Field(default_factory=dict)
    input_files: list[InputFile] = Field(default_factory=list)


class TaskRun(BaseModel):
    session_id: str
    run_id: str | None = None
    prompt: str
    callback_url: str
    callback_token: str
    config: TaskConfig
    sdk_session_id: str | None = None
    callback_base_url: str | None = None
    permission_mode: str = "default"
