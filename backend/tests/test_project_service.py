from datetime import UTC, datetime
import unittest
import uuid
from unittest.mock import MagicMock, call, patch

from app.models.preset import Preset
from app.models.project import Project
from app.models.project_local_mount import ProjectLocalMount
from app.schemas.filesystem import LocalMountConfig
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.project_service import ProjectService


class ProjectServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ProjectService()
        self.db = MagicMock()
        self.user_id = "user-1"
        self.now = datetime.now(UTC)

    @patch("app.services.project_service.PresetRepository.get_visible_by_id")
    @patch("app.services.project_service.ProjectRepository.create")
    def test_create_project_persists_runtime_settings(
        self,
        create: MagicMock,
        get_visible_preset_by_id: MagicMock,
    ) -> None:
        created_project: Project | None = None
        get_visible_preset_by_id.return_value = Preset(
            id=7,
            user_id=self.user_id,
            name="Default preset",
            description=None,
            visual_key="preset-visual-01",
            prompt_template=None,
            browser_enabled=False,
            memory_enabled=False,
            skill_ids=[],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )

        def capture_create(_db: MagicMock, project: Project) -> Project:
            nonlocal created_project
            created_project = project
            project.id = uuid.uuid4()
            project.created_at = self.now
            project.updated_at = self.now
            return project

        create.side_effect = capture_create
        self.db.refresh.side_effect = lambda _: None

        result = self.service.create_project(
            self.db,
            self.user_id,
            ProjectCreateRequest(
                name="Demo",
                description="  Project description  ",
                default_model="  claude-sonnet-4-20250514  ",
                default_preset_id=7,
                local_mounts=[
                    LocalMountConfig(
                        id="workspace",
                        name="  Demo workspace  ",
                        host_path="  /workspace/demo  ",
                        access_mode="rw",
                    ),
                    LocalMountConfig(
                        id="docs",
                        name="  Docs  ",
                        host_path="  /workspace/docs  ",
                        access_mode="ro",
                    ),
                ],
            ),
        )

        self.assertIsNotNone(created_project)
        assert created_project is not None
        self.assertEqual(created_project.description, "Project description")
        self.assertEqual(created_project.default_model, "claude-sonnet-4-20250514")
        self.assertEqual(created_project.default_preset_id, 7)
        self.assertEqual(len(created_project.project_local_mounts), 2)
        self.assertEqual(created_project.project_local_mounts[1].mount_id, "docs")
        self.assertEqual(created_project.project_local_mounts[1].access_mode, "ro")
        self.db.commit.assert_called_once()
        self.assertEqual(result.default_model, "claude-sonnet-4-20250514")
        self.assertEqual(result.default_preset_id, 7)
        self.assertEqual(len(result.local_mounts), 2)
        self.assertEqual(result.local_mounts[0].name, "Demo workspace")
        self.assertEqual(result.local_mounts[1].host_path, "/workspace/docs")

    @patch("app.services.project_service.PresetRepository.get_visible_by_id")
    @patch("app.services.project_service.ProjectRepository.get_visible_by_id")
    def test_update_project_updates_runtime_settings_independently(
        self,
        get_visible_by_id: MagicMock,
        get_visible_preset_by_id: MagicMock,
    ) -> None:
        get_visible_preset_by_id.return_value = Preset(
            id=9,
            user_id=self.user_id,
            name="Updated preset",
            description=None,
            visual_key="preset-visual-01",
            prompt_template=None,
            browser_enabled=False,
            memory_enabled=False,
            skill_ids=[],
            mcp_server_ids=[],
            plugin_ids=[],
            subagent_configs=[],
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )
        project = Project(
            id=uuid.uuid4(),
            user_id=self.user_id,
            scope="personal",
            access_policy="private",
            name="Demo",
            description=None,
            default_model=None,
            default_preset_id=None,
            repo_url=None,
            git_branch=None,
            git_token_env_key=None,
            owner_user_id=self.user_id,
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )
        project.project_local_mounts = [
            ProjectLocalMount(
                mount_id="workspace",
                name="Workspace",
                host_path="/workspace/demo",
                access_mode="rw",
                sort_order=0,
            )
        ]
        get_visible_by_id.return_value = project
        self.db.refresh.side_effect = lambda _: None

        result = self.service.update_project(
            self.db,
            self.user_id,
            project.id,
            ProjectUpdateRequest(
                default_model="  claude-opus-4-1  ",
                default_preset_id=9,
                local_mounts=[
                    LocalMountConfig(
                        id="workspace",
                        name="  Next workspace  ",
                        host_path="  /workspace/next  ",
                        access_mode="ro",
                    ),
                    LocalMountConfig(
                        id="assets",
                        name="Assets",
                        host_path="/workspace/assets",
                        access_mode="rw",
                    ),
                ],
            ),
        )

        self.assertEqual(project.default_model, "claude-opus-4-1")
        self.assertEqual(project.default_preset_id, 9)
        self.assertEqual(len(project.project_local_mounts), 2)
        self.assertEqual(project.project_local_mounts[1].mount_id, "assets")
        self.db.commit.assert_called_once()
        self.assertEqual(result.default_model, "claude-opus-4-1")
        self.assertEqual(result.default_preset_id, 9)
        self.assertEqual(len(result.local_mounts), 2)
        self.assertEqual(result.local_mounts[0].access_mode, "ro")
        self.assertEqual(result.local_mounts[1].id, "assets")

    @patch("app.services.project_service.ProjectRepository.get_visible_by_id")
    def test_update_project_flushes_deleted_mounts_before_reinserting(
        self,
        get_visible_by_id: MagicMock,
    ) -> None:
        project = Project(
            id=uuid.uuid4(),
            user_id=self.user_id,
            scope="personal",
            access_policy="private",
            name="Demo",
            description=None,
            default_model=None,
            repo_url=None,
            git_branch=None,
            git_token_env_key=None,
            owner_user_id=self.user_id,
            is_deleted=False,
            created_at=self.now,
            updated_at=self.now,
        )
        project.project_local_mounts = [
            ProjectLocalMount(
                mount_id="notes",
                name="Notes",
                host_path="/workspace/notes",
                access_mode="rw",
                sort_order=0,
            )
        ]
        get_visible_by_id.return_value = project
        self.db.refresh.side_effect = lambda _: None

        self.service.update_project(
            self.db,
            self.user_id,
            project.id,
            ProjectUpdateRequest(
                local_mounts=[
                    LocalMountConfig(
                        id="notes",
                        name="Notes",
                        host_path="/workspace/new-notes",
                        access_mode="ro",
                    )
                ],
            ),
        )

        self.db.flush.assert_called_once()
        self.assertLess(
            self.db.method_calls.index(call.flush()),
            self.db.method_calls.index(call.commit()),
        )


if __name__ == "__main__":
    unittest.main()
