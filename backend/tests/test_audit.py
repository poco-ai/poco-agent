import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.core.audit import AuditConfig, AuditEvent
from app.models.activity_log import ActivityLog
from app.services.activity_logger import ActivityLogger


class AuditConfigTests(unittest.TestCase):
    def test_exact_rule_overrides_wildcard_rule(self) -> None:
        config = AuditConfig(
            {
                "default": True,
                "workspace.*": False,
                "workspace.invite_created": True,
            }
        )

        self.assertTrue(config.is_enabled("workspace.invite_created"))
        self.assertFalse(config.is_enabled("workspace.member_removed"))

    def test_longest_wildcard_prefix_wins(self) -> None:
        config = AuditConfig(
            {
                "default": False,
                "workspace.*": True,
                "workspace.invite_*": False,
            }
        )

        self.assertFalse(config.is_enabled("workspace.invite_revoked"))
        self.assertTrue(config.is_enabled("workspace.member_role_changed"))


class ActivityLoggerTests(unittest.TestCase):
    def test_log_activity_skips_disabled_action(self) -> None:
        logger = ActivityLogger(AuditConfig({"default": False}))
        db = MagicMock()

        result = logger.log_activity(
            db,
            AuditEvent(
                workspace_id=uuid.uuid4(),
                actor_user_id="user-1",
                action="workspace.created",
                target_type="workspace",
                target_id="target-1",
                metadata={},
            ),
        )

        self.assertIsNone(result)
        db.commit.assert_not_called()

    def test_log_activity_writes_enabled_action(self) -> None:
        logger = ActivityLogger(AuditConfig({"default": True}))
        db = MagicMock()
        now = datetime.now(UTC)
        workspace_id = uuid.uuid4()
        activity_log = ActivityLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_user_id="user-1",
            action="workspace.created",
            target_type="workspace",
            target_id="target-1",
            metadata_json={"name": "Team"},
            created_at=now,
        )

        with patch(
            "app.services.activity_logger.ActivityLogRepository.create",
            return_value=activity_log,
        ) as create_log:
            result = logger.log_activity(
                db,
                AuditEvent(
                    workspace_id=workspace_id,
                    actor_user_id="user-1",
                    action="workspace.created",
                    target_type="workspace",
                    target_id="target-1",
                    metadata={"name": "Team"},
                ),
            )

        create_log.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(activity_log)
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata, {"name": "Team"})


if __name__ == "__main__":
    unittest.main()
