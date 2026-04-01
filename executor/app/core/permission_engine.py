from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PermissionDecision:
    action: str
    rule_id: str
    reason: str


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
        # Plan mode restriction must be checked BEFORE custom rules
        # to prevent bypassing pre-approval restrictions
        if self.permission_mode == "plan" and not self.plan_approved:
            allowed_in_plan_phase = {
                "Read",
                "Grep",
                "Glob",
                "TodoWrite",
                "Task",
                "Skill",
                "AskUserQuestion",
                "ExitPlanMode",
            }
            if tool_name not in allowed_in_plan_phase:
                return PermissionDecision(
                    action="deny",
                    rule_id="preset:plan:pre_approval",
                    reason=f"Tool '{tool_name}' is not allowed in plan mode before approval",
                )

        # Check custom rules after plan mode restriction
        rules = self.policy.get("rules")
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                tools = rule.get("tools")
                if isinstance(tools, list) and tool_name not in tools:
                    continue
                action = str(rule.get("action") or "deny")
                return PermissionDecision(
                    action=action,
                    rule_id=str(rule.get("id") or "custom"),
                    reason=str(rule.get("reason") or "Matched permission rule"),
                )

        default_action = str(self.policy.get("default_action") or "allow")
        return PermissionDecision(
            action=default_action,
            rule_id=f"preset:{self.permission_mode or 'default'}",
            reason="Default permission policy applied",
        )
