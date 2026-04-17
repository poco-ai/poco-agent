import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.preset import Preset
from app.models.project import Project
from app.models.user import User
from app.models.workspace_board import WorkspaceBoard
from app.models.workspace_issue import WorkspaceIssue
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.preset import PresetCopyRequest
from app.schemas.project import ProjectCopyRequest
from app.schemas.workspace_issue import (
    WorkspaceIssueCreateRequest,
    WorkspaceIssueMoveRequest,
)
from app.services.preset_service import PresetService
from app.services.project_service import ProjectService
from app.services.workspace_issue_service import WorkspaceIssueService


class CollaborationPresetServiceTests(unittest.TestCase):
    def test_copy_preset_to_workspace_creates_independent_shared_copy(self) -> None:
        db = MagicMock()
        workspace_id = uuid.uuid4()
        source = Preset(
            id=7,
            user_id="user-1",
            name="Personal Helper",
            description="Source",
            visual_key="preset-visual-01",
            prompt_template="Help",
            browser_enabled=True,
            memory_enabled=False,
            skill_ids=[1],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = Preset(
            id=8,
            user_id="user-1",
            name="Team Helper",
            description="Source",
            visual_key="preset-visual-01",
            prompt_template="Help",
            browser_enabled=True,
            memory_enabled=False,
            skill_ids=[1],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.preset_service.PresetRepository.get_visible_by_id",
                return_value=source,
            ),
            patch(
                "app.services.preset_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.preset_service.PresetRepository.exists_by_scope_name",
                return_value=False,
            ),
            patch(
                "app.services.preset_service.PresetRepository.create",
                side_effect=lambda _db, preset: created,
            ) as create_preset,
            patch.object(PresetService, "_to_response") as to_response,
        ):
            to_response.side_effect = lambda _db, preset: preset
            result = PresetService().copy_preset(
                db,
                "user-1",
                7,
                PresetCopyRequest(
                    target_scope="workspace",
                    workspace_id=workspace_id,
                    name="Team Helper",
                ),
            )

        create_preset.assert_called_once()
        copied = create_preset.call_args.args[1]
        self.assertEqual(copied.scope, "workspace")
        self.assertEqual(copied.workspace_id, workspace_id)
        self.assertEqual(copied.forked_from_preset_id, 7)
        self.assertEqual(copied.created_by, "user-1")
        self.assertIs(result, created)


class CollaborationProjectServiceTests(unittest.TestCase):
    def test_copy_workspace_project_to_personal_omits_local_mounts(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        source = Project(
            id=project_id,
            user_id="user-2",
            name="Shared Project",
            description="Source",
            default_model="claude",
            default_preset_id=None,
            repo_url="https://github.com/acme/repo",
            git_branch="main",
            git_token_env_key=None,
            scope="workspace",
            workspace_id=workspace_id,
            owner_user_id="user-2",
            created_by="user-2",
            updated_by="user-2",
            access_policy="workspace_write",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        source.project_local_mounts = [MagicMock()]
        created = Project(
            id=uuid.uuid4(),
            user_id="user-1",
            scope="personal",
            workspace_id=None,
            owner_user_id="user-1",
            created_by="user-1",
            updated_by="user-1",
            access_policy="private",
            forked_from_project_id=project_id,
            name="Personal Copy",
            description="Source",
            default_model="claude",
            default_preset_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created.project_local_mounts = []

        with (
            patch(
                "app.services.project_service.ProjectRepository.get_visible_by_id",
                return_value=source,
            ),
            patch(
                "app.services.project_service.ProjectRepository.create",
                side_effect=lambda _db, project: created,
            ) as create_project,
        ):
            result = ProjectService().copy_project(
                db,
                "user-1",
                project_id,
                ProjectCopyRequest(target_scope="personal", name="Personal Copy"),
            )

        create_project.assert_called_once()
        copied = create_project.call_args.args[1]
        self.assertEqual(copied.scope, "personal")
        self.assertIsNone(copied.workspace_id)
        self.assertEqual(copied.forked_from_project_id, project_id)
        self.assertEqual(copied.project_local_mounts, [])
        self.assertEqual(result.project_id, created.id)


class WorkspaceIssueServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace_id = uuid.uuid4()
        self.board = WorkspaceBoard(
            id=uuid.uuid4(),
            workspace_id=self.workspace_id,
            name="Team Board",
            description=None,
            created_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def test_create_issue_clears_human_assignee_when_preset_assignee_is_set(
        self,
    ) -> None:
        db = MagicMock()

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.AgentAssignmentService.sync_issue_assignment",
                return_value=None,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceBoardRepository.get_by_id",
                return_value=self.board,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.create",
                side_effect=lambda _db, issue: self._stamp_issue(issue),
            ) as create_issue,
        ):
            WorkspaceIssueService().create_issue(
                db,
                self.current_user,
                self.board.id,
                WorkspaceIssueCreateRequest(
                    title="Investigate flaky tests",
                    assignee_user_id="user-2",
                    assignee_preset_id=9,
                    trigger_mode="persistent_sandbox",
                ),
            )

        issue = create_issue.call_args.args[1]
        self.assertIsNone(issue.assignee_user_id)
        self.assertEqual(issue.assignee_preset_id, 9)

    def test_create_issue_appends_position_within_status_column(self) -> None:
        db = MagicMock()
        existing_issues = [
            self._build_issue(title="A", status="todo", position=0),
            self._build_issue(title="B", status="todo", position=1),
        ]

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceBoardRepository.get_by_id",
                return_value=self.board,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.list_by_board_and_status",
                return_value=existing_issues,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.create",
                side_effect=lambda _db, issue: self._stamp_issue(issue),
            ),
        ):
            result = WorkspaceIssueService().create_issue(
                db,
                self.current_user,
                self.board.id,
                WorkspaceIssueCreateRequest(title="Investigate flaky tests"),
            )

        self.assertEqual(result.position, 2)

    def test_move_issue_to_new_column_reorders_source_and_target_columns(self) -> None:
        db = MagicMock()
        moved_issue = self._build_issue(title="Move me", status="todo", position=1)
        source_issue = self._build_issue(title="Stay", status="todo", position=0)
        target_issue = self._build_issue(title="Done", status="done", position=0)

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.get_by_id",
                return_value=moved_issue,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.list_by_board_and_status",
                side_effect=[[source_issue], [target_issue]],
            ),
            patch(
                "app.services.workspace_issue_service.ActivityLogger.log_activity",
                return_value=None,
            ) as log_activity,
        ):
            result = WorkspaceIssueService().move_issue(
                db,
                self.current_user,
                moved_issue.id,
                WorkspaceIssueMoveRequest(status="done", position=0),
            )

        self.assertEqual(result.status, "done")
        self.assertEqual(result.position, 0)
        self.assertEqual(source_issue.position, 0)
        self.assertEqual(target_issue.position, 1)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(moved_issue)
        log_activity.assert_called_once()
        event = log_activity.call_args.args[1]
        self.assertEqual(event.action, "issue.moved")
        self.assertEqual(
            event.metadata,
            {
                "from_status": "todo",
                "to_status": "done",
                "from_position": 1,
                "to_position": 0,
            },
        )

    def test_move_issue_within_column_reorders_positions(self) -> None:
        db = MagicMock()
        first_issue = self._build_issue(title="First", status="todo", position=0)
        moved_issue = self._build_issue(title="Second", status="todo", position=1)
        third_issue = self._build_issue(title="Third", status="todo", position=2)

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.get_by_id",
                return_value=moved_issue,
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.list_by_board_and_status",
                return_value=[first_issue, third_issue],
            ),
            patch(
                "app.services.workspace_issue_service.ActivityLogger.log_activity",
                return_value=None,
            ) as log_activity,
        ):
            result = WorkspaceIssueService().move_issue(
                db,
                self.current_user,
                moved_issue.id,
                WorkspaceIssueMoveRequest(status="todo", position=0),
            )

        self.assertEqual(result.position, 0)
        self.assertEqual(first_issue.position, 1)
        self.assertEqual(third_issue.position, 2)
        log_activity.assert_not_called()

    def test_move_issue_rejects_unknown_target_status(self) -> None:
        db = MagicMock()
        issue = self._build_issue(title="Move me", status="todo", position=0)

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.get_by_id",
                return_value=issue,
            ),
        ):
            with self.assertRaises(AppException) as exc:
                WorkspaceIssueService().move_issue(
                    db,
                    self.current_user,
                    issue.id,
                    WorkspaceIssueMoveRequest.model_construct(
                        status="blocked",
                        position=0,
                    ),
                )

        self.assertEqual(exc.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_delete_issue_returns_deleted_payload(self) -> None:
        db = MagicMock()
        issue = self._build_issue(title="Delete me", status="todo", position=0)

        with (
            patch(
                "app.services.workspace_issue_service.require_workspace_member",
                return_value=MagicMock(role="member", status="active"),
            ),
            patch(
                "app.services.workspace_issue_service.WorkspaceIssueRepository.get_by_id",
                return_value=issue,
            ),
        ):
            result = WorkspaceIssueService().delete_issue(
                db,
                self.current_user,
                issue.id,
            )

        self.assertEqual(result.issue_id, issue.id)
        db.delete.assert_called_once_with(issue)
        db.commit.assert_called_once()

    def _build_issue(self, title: str, status: str, position: int) -> WorkspaceIssue:
        return self._stamp_issue(
            WorkspaceIssue(
                id=uuid.uuid4(),
                workspace_id=self.workspace_id,
                board_id=self.board.id,
                title=title,
                description=None,
                status=status,
                position=position,
                type="task",
                priority="medium",
                due_date=None,
                assignee_user_id=None,
                assignee_preset_id=None,
                reporter_user_id=None,
                related_project_id=None,
                creator_user_id="user-1",
                updated_by="user-1",
            )
        )

    @staticmethod
    def _stamp_issue(issue):
        now = datetime.now(UTC)
        if getattr(issue, "id", None) is None:
            issue.id = uuid.uuid4()
        issue.created_at = now
        issue.updated_at = now
        return issue


if __name__ == "__main__":
    unittest.main()
