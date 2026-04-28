import unittest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.schemas.input_file import InputFile
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest
from app.services.task_service import TaskService


class TaskServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TaskService()
        self.db = MagicMock()
        self.user_id = "user-1"

    @patch("app.services.task_service.env_var_service.get_system_env_map")
    @patch.object(TaskService, "_build_user_mcp_server_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_skill_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_plugin_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_subagent_ids_defaults", return_value=[])
    def test_build_config_snapshot_accepts_models_from_system_env_catalog(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        get_system_env_map: MagicMock,
    ) -> None:
        get_system_env_map.return_value = {
            "DEFAULT_MODEL": "minimax-default",
            "MODEL_LIST": "minimax-default,minimax-coder",
        }

        result = self.service._build_config_snapshot(
            self.db,
            self.user_id,
            TaskConfig(model="minimax-coder"),
            base_config={},
        )

        self.assertEqual(result["model"], "minimax-coder")
        self.assertEqual(result["model_provider_id"], "minimax")

    @patch("app.services.task_service.env_var_service.get_system_env_map")
    @patch.object(TaskService, "_build_user_mcp_server_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_skill_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_plugin_ids_defaults", return_value=[])
    @patch.object(TaskService, "_build_user_subagent_ids_defaults", return_value=[])
    def test_build_config_snapshot_normalizes_system_default_model_override(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        ____: MagicMock,
        get_system_env_map: MagicMock,
    ) -> None:
        get_system_env_map.return_value = {
            "DEFAULT_MODEL": "minimax-default",
            "MODEL_LIST": "minimax-default,minimax-coder",
        }

        result = self.service._build_config_snapshot(
            self.db,
            self.user_id,
            TaskConfig(model="minimax-default"),
            base_config={},
        )

        self.assertNotIn("model", result)
        self.assertNotIn("model_provider_id", result)

    @patch.object(TaskService, "_build_project_input_files")
    @patch.object(TaskService, "_apply_project_repo_defaults")
    @patch.object(TaskService, "_build_config_snapshot")
    @patch("app.services.task_service.SessionQueueService")
    @patch("app.services.task_service.RunRepository.get_blocking_by_session")
    @patch("app.services.task_service.SessionRepository.get_by_id_for_update")
    @patch("app.services.task_service.ProjectRepository.get_by_id")
    def test_follow_up_run_reloads_project_for_project_files(
        self,
        get_project_by_id: MagicMock,
        get_session_by_id_for_update: MagicMock,
        get_blocking_by_session: MagicMock,
        session_queue_service_cls: MagicMock,
        build_config_snapshot: MagicMock,
        apply_project_repo_defaults: MagicMock,
        build_project_input_files: MagicMock,
    ) -> None:
        project_id = uuid4()
        session_id = uuid4()
        project = MagicMock(id=project_id, user_id=self.user_id)
        session = MagicMock(
            id=session_id,
            user_id=self.user_id,
            project_id=project_id,
            kind="chat",
            config_snapshot={},
        )
        run_item = MagicMock(id=uuid4(), status="running")
        run = MagicMock(id=uuid4(), status="running")

        get_project_by_id.return_value = project
        get_session_by_id_for_update.return_value = session
        get_blocking_by_session.return_value = None
        build_config_snapshot.return_value = {}
        apply_project_repo_defaults.side_effect = lambda config, _project: config
        build_project_input_files.return_value = [
            InputFile(
                name="guide.md",
                source="project://guide.md",
                size=12,
                content_type="text/markdown",
            )
        ]

        session_queue_service = session_queue_service_cls.return_value
        session_queue_service.get_existing_enqueue_response.return_value = None
        session_queue_service.materialize_run.return_value = (run_item, run)
        session_queue_service.count_active_items.return_value = 0

        result = self.service.enqueue_task(
            self.db,
            self.user_id,
            TaskEnqueueRequest(prompt="hello", session_id=session_id),
        )

        get_project_by_id.assert_called_once_with(self.db, project_id)
        build_project_input_files.assert_called_once_with(self.db, project)
        self.assertEqual(
            session_queue_service.materialize_run.call_args.kwargs[
                "run_config_snapshot"
            ]["input_files"][0]["name"],
            "guide.md",
        )
        self.assertEqual(result.accepted_type, "run")
        self.assertEqual(result.session_id, session_id)


if __name__ == "__main__":
    unittest.main()
