from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from app.schemas.permission_policy import PermissionPolicy


class HookSpec(BaseModel):
    key: str
    phase: Literal["setup", "pre_query", "message", "error", "teardown"] = "message"
    order: int = 100
    enabled: bool = True
    on_error: Literal["continue", "fail"] = "continue"
    config: dict[str, Any] = Field(default_factory=dict)


class HookPipelineSettings(BaseModel):
    pipeline: list[HookSpec] = Field(default_factory=list)


class WorkspaceExecutionSettings(BaseModel):
    checkout_strategy: (
        Literal[
            "clone",
            "worktree",
            "sparse-clone",
            "sparse-worktree",
        ]
        | None
    ) = None
    sparse_paths: list[str] = Field(default_factory=list)
    reference_branch: str | None = None


class ExecutionSettings(BaseModel):
    schema_version: str = "v1"
    hooks: HookPipelineSettings = Field(default_factory=HookPipelineSettings)
    permissions: Union[PermissionPolicy, dict[str, Any]] = Field(
        default_factory=PermissionPolicy
    )
    workspace: WorkspaceExecutionSettings = Field(
        default_factory=WorkspaceExecutionSettings
    )
    skills: dict[str, Any] = Field(default_factory=dict)


class ExecutionSettingsUpdateRequest(BaseModel):
    settings: ExecutionSettings


class SkillManifestValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
