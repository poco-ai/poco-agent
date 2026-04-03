from __future__ import annotations

import fnmatch
import os
import re
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
    invalid_paths: list[str] = field(default_factory=list)
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

_PATH_INPUT_KEYS = ("file_path", "path", "file")
_URL_INPUT_KEYS = ("url", "endpoint", "host", "hostname", "target")
_MCP_TOOL_PREFIX_RE = re.compile(r"^mcp__([^_]+)__")
_URL_RE = re.compile(r"https?://([^/\s\"']+)")
_HOSTNAME_RE = re.compile(r"(?:^|\s)(?:curl|wget|ssh|nc|ncat)\s+.*?([a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,})")


def _normalize_path(raw_path: str, cwd: str) -> str | None:
    """Normalize *raw_path* against *cwd*.

    Returns the normalized absolute path, or ``None`` when the result
    escapes *cwd* (path-traversal attempt).
    """
    clean = raw_path.strip().strip("\"'")
    if not clean:
        return None

    normed = os.path.normpath(clean)
    if not os.path.isabs(normed):
        if not cwd:
            parts = [part for part in re.split(r"[\\/]+", normed) if part]
            if ".." in parts:
                return None
            return normed
        normed = os.path.normpath(os.path.join(cwd, normed))

    if cwd:
        base = os.path.normcase(os.path.normpath(cwd))
        candidate = os.path.normcase(normed)
        try:
            if os.path.commonpath([base, candidate]) != base:
                return None
        except ValueError:
            return None

    return normed


class PermissionContextBuilder:
    @staticmethod
    def build(
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> PermissionContext:
        cwd = context.get("cwd", "")

        normalized_paths, invalid_paths = PermissionContextBuilder._extract_paths(
            tool_name, tool_input, cwd
        )
        network_targets = PermissionContextBuilder._extract_network_targets(
            tool_name, tool_input
        )
        mcp_server_name = PermissionContextBuilder._extract_mcp_server(
            tool_name, tool_input
        )

        return PermissionContext(
            tool_name=tool_name,
            tool_category=_TOOL_CATEGORIES.get(tool_name, "execute"),
            tool_input=tool_input,
            cwd=cwd,
            normalized_paths=normalized_paths,
            invalid_paths=invalid_paths,
            network_targets=network_targets,
            mcp_server_name=mcp_server_name,
            session_id=context.get("session_id", ""),
            run_id=context.get("run_id"),
        )

    @staticmethod
    def _extract_paths(
        tool_name: str,
        tool_input: dict[str, Any],
        cwd: str,
    ) -> tuple[list[str], list[str]]:
        raw_paths: list[str] = []
        for key in _PATH_INPUT_KEYS:
            val = tool_input.get(key)
            if isinstance(val, str) and val:
                raw_paths.append(val)

        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if isinstance(cmd, str):
                raw_paths.extend(_extract_paths_from_command(cmd))

        valid_paths: list[str] = []
        invalid_paths: list[str] = []
        for rp in raw_paths:
            normed = _normalize_path(rp, cwd)
            if normed is None:
                invalid_paths.append(rp)
            else:
                valid_paths.append(normed)
        return valid_paths, invalid_paths

    @staticmethod
    def _extract_network_targets(
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> list[str]:
        targets: list[str] = []
        for key in _URL_INPUT_KEYS:
            val = tool_input.get(key)
            if isinstance(val, str) and val:
                targets.append(val)

        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if isinstance(cmd, str):
                for m in _URL_RE.finditer(cmd):
                    targets.append(m.group(1))
                for m in _HOSTNAME_RE.finditer(cmd):
                    targets.append(m.group(1))

        return targets

    @staticmethod
    def _extract_mcp_server(
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> str | None:
        for key in ("mcp_server", "server_name"):
            val = tool_input.get(key)
            if isinstance(val, str) and val:
                return val

        m = _MCP_TOOL_PREFIX_RE.match(tool_name)
        if m:
            return m.group(1)

        return None


def _extract_paths_from_command(cmd: str) -> list[str]:
    """Best-effort extraction of file paths from a shell command string."""
    paths: list[str] = []
    tokens = cmd.split()
    for token in tokens:
        if token.startswith("-"):
            continue
        if os.sep in token or "/" in token or token.startswith("."):
            cleaned = token.strip("\"'")
            if cleaned:
                paths.append(cleaned)
    return paths


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

        # Custom rules (sorted by priority, deny wins at same priority)
        rules = self.policy.get("rules")
        if isinstance(rules, list):
            pctx = PermissionContextBuilder.build(tool_name, tool_input, context)
            if pctx.invalid_paths:
                return PermissionDecision(
                    action="deny",
                    rule_id="preset:path:outside_cwd",
                    reason="Path escapes current working directory",
                )
            sorted_rules = sorted(
                (r for r in rules if isinstance(r, dict) and r.get("enabled", True)),
                key=lambda r: _safe_priority(r),
            )
            matched: list[dict[str, Any]] = []
            matched_priority: int | None = None
            for rule in sorted_rules:
                prio = _safe_priority(rule)
                if matched_priority is not None and prio > matched_priority:
                    break
                if self._matches_rule(rule, pctx):
                    matched.append(rule)
                    matched_priority = prio

            if matched:
                deny = next(
                    (r for r in matched if str(r.get("action") or "deny") == "deny"),
                    None,
                )
                winner = deny if deny is not None else matched[0]
                return PermissionDecision(
                    action=str(winner.get("action") or "deny"),
                    rule_id=str(winner.get("id") or "custom"),
                    reason=str(winner.get("reason") or "Matched permission rule"),
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
        pctx: PermissionContext,
    ) -> bool:
        match_spec = rule.get("match")
        if not isinstance(match_spec, dict):
            # Legacy: rule has top-level "tools" list
            tools = rule.get("tools")
            if isinstance(tools, list):
                return pctx.tool_name in tools
            return True

        # New-style match conditions (all must match)
        tools = match_spec.get("tools")
        if isinstance(tools, list) and pctx.tool_name not in tools:
            return False

        tool_categories = match_spec.get("tool_categories")
        if isinstance(tool_categories, list):
            if pctx.tool_category not in tool_categories:
                return False

        path_patterns = match_spec.get("path_patterns")
        if isinstance(path_patterns, list) and path_patterns:
            if not pctx.normalized_paths or not any(
                fnmatch.fnmatch(p, pat)
                for p in pctx.normalized_paths
                for pat in path_patterns
            ):
                return False

        network_patterns = match_spec.get("network_patterns")
        if isinstance(network_patterns, list) and network_patterns:
            if not pctx.network_targets or not any(
                fnmatch.fnmatch(t, pat)
                for t in pctx.network_targets
                for pat in network_patterns
            ):
                return False

        mcp_servers = match_spec.get("mcp_servers")
        if isinstance(mcp_servers, list) and mcp_servers:
            if pctx.mcp_server_name not in mcp_servers:
                return False

        return True
