import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.preset import Preset
from app.models.user import User
from app.models.workspace_issue import WorkspaceIssue
from app.services.agent_assignment_service import AgentAssignmentService


class AgentAssignmentServiceTests(unittest.TestCase):
    def test_sync_issue_assignment_prepares_persistent_assignment(self) -> None:
        db = MagicMock()
        issue_id = uuid.uuid4()
        issue = WorkspaceIssue(
            id=issue_id,
            workspace_id=uuid.uuid4(),
            board_id=uuid.uuid4(),
            title="Add rate limiting",
            description="Protect every API endpoint.",
            status="todo",
            type="task",
            priority="high",
            assignee_preset_id=None,
            creator_user_id="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        preset = Preset(
            id=9,
            user_id="user-1",
            name="Backend Specialist",
            visual_key="preset-visual-01",
            prompt_template="",
            browser_enabled=False,
            memory_enabled=False,
            container_mode="persistent",
            skill_ids=[],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        service = AgentAssignmentService(task_service=MagicMock())

        with (
            patch(
                "app.services.agent_assignment_service.AgentAssignmentRepository.get_by_issue_id",
                return_value=None,
            ),
            patch(
                "app.services.agent_assignment_service.PresetRepository.get_visible_by_id",
                return_value=preset,
            ),
            patch.object(service, "_enqueue_run", return_value=MagicMock()) as enqueue_run,
            patch.object(
                service._prompt_builder,
                "build_issue_prompt",
                return_value="Add rate limiting\n\nProtect every API endpoint.",
            ),
        ):
            assignment = service.sync_issue_assignment(
                db,
                current_user=current_user,
                issue=issue,
                preset_id=9,
                trigger_mode="persistent_sandbox",
                schedule_cron=None,
                prompt_override=None,
                auto_trigger=True,
            )

        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.trigger_mode, "persistent_sandbox")
        self.assertEqual(issue.status, "in_progress")
        self.assertEqual(assignment.prompt, "Add rate limiting\n\nProtect every API endpoint.")
        enqueue_run.assert_called_once()

    def test_sync_callback_status_marks_issue_done(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        assignment = MagicMock(
            workspace_id=uuid.uuid4(),
            issue_id=uuid.uuid4(),
            created_by="user-1",
            id=uuid.uuid4(),
        )
        issue = MagicMock()
        issue.id = assignment.issue_id
        issue.status = "in_progress"

        with (
            patch(
                "app.services.agent_assignment_service.AgentAssignmentRepository.get_by_session_id",
                return_value=assignment,
            ),
            patch(
                "app.services.agent_assignment_service.WorkspaceIssueRepository.get_by_id",
                return_value=issue,
            ),
        ):
            AgentAssignmentService().sync_callback_status(
                db,
                session_id=session_id,
                callback_status="completed",
            )

        self.assertEqual(assignment.status, "completed")
        self.assertEqual(issue.status, "done")
        self.assertIsNotNone(assignment.last_completed_at)


if __name__ == "__main__":
    unittest.main()
