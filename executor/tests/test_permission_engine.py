from app.core.permission_engine import PermissionContextBuilder, PermissionEngine


def test_plan_mode_denies_write_before_approval() -> None:
    engine = PermissionEngine.from_permission_mode("plan", plan_approved=False)

    decision = engine.evaluate("Write", {}, {})

    assert decision.action == "deny"
    assert decision.rule_id == "preset:plan:pre_approval"


def test_custom_policy_allows_matching_tool() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "deny",
            "rules": [
                {
                    "id": "allow-read",
                    "tools": ["Read"],
                    "action": "allow",
                    "reason": "Read access is allowed",
                }
            ],
        },
        plan_approved=True,
    )

    allowed = engine.evaluate("Read", {}, {})
    denied = engine.evaluate("Write", {}, {})

    assert allowed.action == "allow"
    assert allowed.rule_id == "allow-read"
    assert denied.action == "deny"


def test_priority_rules_ordered() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-bash-high-prio",
                    "priority": 10,
                    "tools": ["Bash"],
                    "action": "deny",
                    "reason": "Bash denied by high-priority rule",
                },
                {
                    "id": "allow-bash-low-prio",
                    "priority": 50,
                    "tools": ["Bash"],
                    "action": "allow",
                    "reason": "Bash allowed by low-priority rule",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Bash", {}, {})
    assert decision.action == "deny"
    assert decision.rule_id == "deny-bash-high-prio"


def test_match_tool_categories() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-write-cat",
                    "priority": 10,
                    "match": {
                        "tool_categories": ["write"],
                    },
                    "action": "deny",
                    "reason": "Write category denied",
                },
            ],
        },
        plan_approved=True,
    )

    assert engine.evaluate("Edit", {}, {}).action == "deny"
    assert engine.evaluate("Write", {}, {}).action == "deny"
    assert engine.evaluate("Read", {}, {}).action == "allow"


def test_disabled_rule_skipped() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-bash",
                    "tools": ["Bash"],
                    "action": "deny",
                    "reason": "Bash denied",
                    "enabled": False,
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Bash", {}, {})
    assert decision.action == "allow"


def test_plan_mode_allows_read_tools_before_approval() -> None:
    engine = PermissionEngine.from_permission_mode("plan", plan_approved=False)

    for tool in ["Read", "Grep", "Glob", "TodoWrite", "ExitPlanMode"]:
        decision = engine.evaluate(tool, {}, {})
        assert decision.action == "allow", f"{tool} should be allowed in plan mode"


def test_default_mode_allows_all() -> None:
    engine = PermissionEngine.from_permission_mode("default", plan_approved=True)

    assert engine.evaluate("Write", {}, {}).action == "allow"
    assert engine.evaluate("Bash", {}, {}).action == "allow"
    assert engine.evaluate("Read", {}, {}).action == "allow"


def test_new_style_match_with_tools() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "deny",
            "rules": [
                {
                    "id": "allow-read-write",
                    "priority": 10,
                    "match": {
                        "tools": ["Read", "Edit", "Write"],
                    },
                    "action": "allow",
                    "reason": "Read/write tools allowed",
                },
            ],
        },
        plan_approved=True,
    )

    assert engine.evaluate("Read", {}, {}).action == "allow"
    assert engine.evaluate("Edit", {}, {}).action == "allow"
    assert engine.evaluate("Bash", {}, {}).action == "deny"


def test_invalid_priority_falls_back_to_default_order() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-bash-invalid-priority",
                    "priority": "",
                    "tools": ["Bash"],
                    "action": "deny",
                    "reason": "Invalid priority falls back to default",
                },
                {
                    "id": "allow-bash-lower-priority",
                    "priority": 200,
                    "tools": ["Bash"],
                    "action": "allow",
                    "reason": "Lower priority allow rule",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Bash", {}, {})
    assert decision.action == "deny"
    assert decision.rule_id == "deny-bash-invalid-priority"


def test_path_pattern_match_deny() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-py-files",
                    "priority": 10,
                    "match": {"path_patterns": ["*.py"]},
                    "action": "deny",
                    "reason": "Python files denied",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Edit", {"file_path": "test.py"}, {"cwd": "/workspace"})
    assert decision.action == "deny"
    assert decision.rule_id == "deny-py-files"


def test_path_pattern_no_match_skipped() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-py-files",
                    "priority": 10,
                    "match": {"path_patterns": ["*.py"]},
                    "action": "deny",
                    "reason": "Python files denied",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate(
        "Edit", {"file_path": "test.txt"}, {"cwd": "/workspace"}
    )
    assert decision.action == "allow"


def test_path_traversal_blocked() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-all-paths",
                    "priority": 10,
                    "match": {"path_patterns": ["*"]},
                    "action": "deny",
                    "reason": "All file access denied",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate(
        "Read", {"file_path": "../../etc/passwd"}, {"cwd": "/workspace"}
    )
    assert decision.action == "deny"
    assert decision.rule_id == "preset:path:outside_cwd"

    ctx = PermissionContextBuilder.build(
        "Read", {"file_path": "../../etc/passwd"}, {"cwd": "/workspace"}
    )
    assert not ctx.normalized_paths
    assert ctx.invalid_paths == ["../../etc/passwd"]


def test_network_pattern_match() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-evil",
                    "priority": 10,
                    "match": {"network_patterns": ["*.evil.com"]},
                    "action": "deny",
                    "reason": "Evil domain denied",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate(
        "Bash",
        {"command": "curl https://api.evil.com/data"},
        {},
    )
    assert decision.action == "deny"
    assert decision.rule_id == "deny-evil"


def test_mcp_server_match() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "deny-dangerous-mcp",
                    "priority": 10,
                    "match": {"mcp_servers": ["dangerous-server"]},
                    "action": "deny",
                    "reason": "Dangerous MCP server denied",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate(
        "mcp__dangerous-server__run", {}, {}
    )
    assert decision.action == "deny"
    assert decision.rule_id == "deny-dangerous-mcp"


def test_deny_wins_same_priority() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [
                {
                    "id": "allow-bash",
                    "priority": 10,
                    "tools": ["Bash"],
                    "action": "allow",
                    "reason": "Allow Bash",
                },
                {
                    "id": "deny-bash",
                    "priority": 10,
                    "tools": ["Bash"],
                    "action": "deny",
                    "reason": "Deny Bash",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Bash", {}, {})
    assert decision.action == "deny"
    assert decision.rule_id == "deny-bash"


def test_ask_action_returned() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "deny",
            "rules": [
                {
                    "id": "ask-bash",
                    "priority": 10,
                    "tools": ["Bash"],
                    "action": "ask",
                    "reason": "Ask before running Bash",
                },
            ],
        },
        plan_approved=True,
    )

    decision = engine.evaluate("Bash", {}, {})
    assert decision.action == "ask"
    assert decision.rule_id == "ask-bash"


def test_path_escape_denied_even_without_matching_rule() -> None:
    engine = PermissionEngine(
        policy={
            "default_action": "allow",
            "rules": [],
        },
        plan_approved=True,
    )

    traversal = engine.evaluate(
        "Read", {"file_path": "../../etc/passwd"}, {"cwd": "/workspace"}
    )
    outside_root = engine.evaluate(
        "Read", {"file_path": "/workspace-private/secret.txt"}, {"cwd": "/workspace"}
    )

    assert traversal.action == "deny"
    assert traversal.rule_id == "preset:path:outside_cwd"
    assert outside_root.action == "deny"
    assert outside_root.rule_id == "preset:path:outside_cwd"
