from app.core.permission_engine import PermissionEngine


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
