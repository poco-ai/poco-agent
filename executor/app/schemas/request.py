from typing import Any, Literal

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


class HookSpec(BaseModel):
    key: str
    phase: Literal["setup", "pre_query", "message", "error", "teardown"] = "message"
    order: int = 100
    enabled: bool = True
    on_error: Literal["continue", "fail"] = "continue"
    config: dict[str, Any] = Field(default_factory=dict)


class TaskConfig(BaseModel):
    repo_url: str | None = None
    git_branch: str = "main"
    # Optional env var key holding a GitHub token (non-secret; used by manager).
    git_token_env_key: str | None = None
    # Optional explicit model override for this run.
    model: str | None = None
    # Resolved GitHub token (secret) injected by Executor Manager at runtime.
    git_token: str | None = None
    # Runtime-only provider credentials injected by Executor Manager for this run.
    env_overrides: dict[str, str] = Field(default_factory=dict)
    # Built-in browser capability toggle (Playwright MCP is injected internally by the executor).
    browser_enabled: bool = False
    # Built-in memory capability toggle (Memory MCP is injected internally by the executor).
    memory_enabled: bool = False
    mcp_config: dict = Field(default_factory=dict)
    mcp_server_ids: list[int] = Field(default_factory=list)
    skill_files: dict = Field(default_factory=dict)
    skill_ids: list[int] = Field(default_factory=list)
    plugin_files: dict = Field(default_factory=dict)
    plugin_ids: list[int] = Field(default_factory=list)
    agents: dict[str, AgentDefinition] = Field(default_factory=dict)
    input_files: list[InputFile] = Field(default_factory=list)
    execution_settings: dict[str, Any] = Field(default_factory=dict)
    hook_specs: list[HookSpec] = Field(default_factory=list)
    permission_policy: dict[str, Any] = Field(default_factory=dict)
    workspace_strategy: (
        Literal[
            "clone",
            "worktree",
            "sparse-clone",
            "sparse-worktree",
        ]
        | None
    ) = None
    workspace_sparse_paths: list[str] = Field(default_factory=list)
    workspace_reference_branch: str | None = None


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
