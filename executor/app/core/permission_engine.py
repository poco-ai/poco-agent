from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PermissionDecision:
    action: str
    rule_id: str
    reason: str


@dataclass(slots=True)
class PermissionContext:
    tool_name: str
    tool_category: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    cwd: str = ""
    normalized_paths: list[str] = field(default_factory=list)
    network_targets: list[str] = field(default_factory=list)
    mcp_server_name: str | None = None
    session_id: str = ""
    run_id: str | None = None


_TOOL_CATEGORIES: dict[str, str] = {
    "Read": "read",
    "Grep": "read",
    "Glob": "read",
    "Edit": "write",
    "Write": "write",
    "Bash": "execute",
    "TodoWrite": "write",
    "Task": "execute",
    "Skill": "execute",
    "AskUserQuestion": "read",
    "ExitPlanMode": "read",
    "Agent": "execute",
}


class PermissionContextBuilder:
    @staticmethod
    def build(
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> PermissionContext:
        return PermissionContext(
            tool_name=tool_name,
            tool_category=_TOOL_CATEGORIES.get(tool_name, "execute"),
            tool_input=tool_input,
            cwd=context.get("cwd", ""),
            session_id=context.get("session_id", ""),
            run_id=context.get("run_id"),
        )


class PresetPolicyCompiler:
    _PLAN_ALLOWED = frozenset(
        {
            "Read",
            "Grep",
            "Glob",
            "TodoWrite",
            "Task",
            "Skill",
            "AskUserQuestion",
            "ExitPlanMode",
        }
    )

    @classmethod
    def compile(cls, permission_mode: str) -> list[dict[str, Any]]:
        if permission_mode == "plan":
            return [
                {
                    "id": "preset:plan:pre_approval",
                    "priority": 0,
                    "match": {},
                    "action": "deny",
                    "reason": "Plan mode pre-approval restriction",
                    "_plan_restriction": True,
                }
            ]
        return []


def _safe_priority(rule: dict[str, Any]) -> int:
    raw_priority = rule.get("priority", 100)
    if raw_priority in (None, ""):
        return 100
    try:
        return int(raw_priority)
    except (TypeError, ValueError):
        return 100


class PermissionEngine:
    def __init__(
        self,
        *,
        policy: dict[str, Any] | None = None,
        permission_mode: str = "default",
        plan_approved: bool = True,
    ) -> None:
        self.policy = policy or {}
        self.permission_mode = permission_mode
        self.plan_approved = plan_approved
        self._preset_rules = PresetPolicyCompiler.compile(permission_mode)

    @classmethod
    def from_permission_mode(
        cls, permission_mode: str, *, plan_approved: bool
    ) -> "PermissionEngine":
        return cls(
            policy={},
            permission_mode=permission_mode,
            plan_approved=plan_approved,
        )

    def evaluate(
        self, tool_name: str, tool_input: dict[str, Any], context: dict[str, Any]
    ) -> PermissionDecision:
        # Plan mode preset restriction (highest priority, hard-coded)
        if self.permission_mode == "plan" and not self.plan_approved:
            allowed_in_plan_phase = PresetPolicyCompiler._PLAN_ALLOWED
            if tool_name not in allowed_in_plan_phase:
                return PermissionDecision(
                    action="deny",
                    rule_id="preset:plan:pre_approval",
                    reason=f"Tool '{tool_name}' is not allowed in plan mode before approval",
                )

        # Custom rules (sorted by priority)
        rules = self.policy.get("rules")
        if isinstance(rules, list):
            sorted_rules = sorted(
                (r for r in rules if isinstance(r, dict) and r.get("enabled", True)),
                key=lambda r: _safe_priority(r),
            )
            for rule in sorted_rules:
                if self._matches_rule(rule, tool_name, tool_input, context):
                    action = str(rule.get("action") or "deny")
                    return PermissionDecision(
                        action=action,
                        rule_id=str(rule.get("id") or "custom"),
                        reason=str(rule.get("reason") or "Matched permission rule"),
                    )

        # Default
        default_action = str(self.policy.get("default_action") or "allow")
        return PermissionDecision(
            action=default_action,
            rule_id=f"preset:{self.permission_mode or 'default'}",
            reason="Default permission policy applied",
        )

    def _matches_rule(
        self,
        rule: dict[str, Any],
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        match_spec = rule.get("match")
        if not isinstance(match_spec, dict):
            # Legacy: rule has top-level "tools" list
            tools = rule.get("tools")
            if isinstance(tools, list):
                return tool_name in tools
            return True

        # New-style match conditions (all must match)
        tools = match_spec.get("tools")
        if isinstance(tools, list) and tool_name not in tools:
            return False

        tool_categories = match_spec.get("tool_categories")
        if isinstance(tool_categories, list):
            tool_cat = _TOOL_CATEGORIES.get(tool_name, "execute")
            if tool_cat not in tool_categories:
                return False

        return True
