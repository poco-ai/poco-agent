from typing import Any, Literal

from pydantic import BaseModel, Field


class PermissionRuleMatch(BaseModel):
    tools: list[str] | None = None
    tool_categories: list[str] | None = None
    path_patterns: list[str] | None = None
    network_patterns: list[str] | None = None
    mcp_servers: list[str] | None = None


class PermissionRule(BaseModel):
    id: str
    priority: int = 100
    match: PermissionRuleMatch = Field(default_factory=PermissionRuleMatch)
    action: Literal["allow", "deny", "ask"]
    reason: str = ""
    enabled: bool = True


class PermissionPolicy(BaseModel):
    version: str = "v1"
    mode: Literal["audit", "enforce"] = "audit"
    default_action: Literal["allow", "deny"] = "allow"
    preset_source: str | None = None
    rules: list[PermissionRule] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PermissionPolicy":
        if data is None or not data:
            return cls()
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)


class PermissionAuditEventResponse(BaseModel):
    id: str
    run_id: str
    session_id: str
    tool_name: str
    tool_input: dict[str, Any] | None = None
    policy_action: str
    policy_rule_id: str | None = None
    policy_reason: str | None = None
    audit_mode: bool
    context: dict[str, Any] | None = None
    created_at: str
