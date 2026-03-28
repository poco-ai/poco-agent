import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.task_service import TaskService


class TestTaskServiceResolveSchedule(unittest.TestCase):
    """Test _resolve_schedule instance method."""

    def test_empty_schedule_mode(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = ""
        request.scheduled_at = None
        request.timezone = None
        with self.assertRaises(AppException) as ctx:
            service._resolve_schedule(request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_schedule_mode_scheduled_without_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "scheduled"
        request.scheduled_at = None
        request.timezone = None
        with self.assertRaises(AppException) as ctx:
            service._resolve_schedule(request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_schedule_mode_scheduled_with_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "scheduled"
        request.scheduled_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        request.timezone = None
        mode, at = service._resolve_schedule(request)
        self.assertEqual(mode, "scheduled")
        self.assertIsNotNone(at)

    def test_schedule_mode_immediate_without_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        mode, at = service._resolve_schedule(request)
        self.assertEqual(mode, "immediate")
        self.assertIsNone(at)

    def test_schedule_mode_immediate_with_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "immediate"
        request.scheduled_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        request.timezone = None
        mode, at = service._resolve_schedule(request)
        # Should treat as scheduled when scheduled_at is provided
        self.assertEqual(mode, "scheduled")
        self.assertIsNotNone(at)

    def test_schedule_mode_nightly_without_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "nightly"
        request.scheduled_at = None
        request.timezone = None
        mode, at = service._resolve_schedule(request)
        self.assertEqual(mode, "nightly")
        self.assertIsNone(at)

    def test_schedule_mode_nightly_with_scheduled_at(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "nightly"
        request.scheduled_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        request.timezone = None
        with self.assertRaises(AppException) as ctx:
            service._resolve_schedule(request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_other_schedule_mode(self) -> None:
        service = TaskService()
        request = MagicMock()
        request.schedule_mode = "custom"
        request.scheduled_at = None
        request.timezone = None
        mode, at = service._resolve_schedule(request)
        self.assertEqual(mode, "custom")
        self.assertIsNone(at)


class TestTaskServiceValidateAndNormalizeModel(unittest.TestCase):
    """Test _validate_and_normalize_model static method."""

    def test_non_dict_config(self) -> None:
        # Should not raise
        TaskService._validate_and_normalize_model("not a dict")

    def test_no_model_key(self) -> None:
        config = {"other": "value"}
        TaskService._validate_and_normalize_model(config)
        self.assertNotIn("model_provider_id", config)

    def test_model_is_none(self) -> None:
        config = {"model": None}
        TaskService._validate_and_normalize_model(config)
        self.assertNotIn("model", config)
        self.assertNotIn("model_provider_id", config)

    def test_model_not_string(self) -> None:
        config = {"model": 123}
        with self.assertRaises(AppException) as ctx:
            TaskService._validate_and_normalize_model(config)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_model_empty_string(self) -> None:
        config = {"model": "   "}
        TaskService._validate_and_normalize_model(config)
        self.assertNotIn("model", config)
        self.assertNotIn("model_provider_id", config)

    @patch("app.services.task_service.get_settings")
    def test_model_equals_default(self, mock_settings: MagicMock) -> None:
        settings = MagicMock()
        settings.default_model = "default-model"
        mock_settings.return_value = settings

        config = {"model": "default-model"}
        TaskService._validate_and_normalize_model(config)
        self.assertNotIn("model", config)
        self.assertNotIn("model_provider_id", config)

    @patch("app.services.task_service.get_allowed_model_ids")
    @patch("app.services.task_service.get_settings")
    def test_model_valid(
        self, mock_settings: MagicMock, mock_allowed: MagicMock
    ) -> None:
        settings = MagicMock()
        settings.default_model = "default-model"
        mock_settings.return_value = settings
        mock_allowed.return_value = ["allowed-model", "other-model"]

        config = {"model": "allowed-model"}
        TaskService._validate_and_normalize_model(config)
        self.assertEqual(config["model"], "allowed-model")

    def test_model_provider_id_not_string(self) -> None:
        config = {"model": "some-model", "model_provider_id": 123}
        with self.assertRaises(AppException) as ctx:
            TaskService._validate_and_normalize_model(config)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.task_service.get_allowed_model_ids")
    @patch("app.services.task_service.get_settings")
    def test_model_provider_id_empty(
        self, mock_settings: MagicMock, mock_allowed: MagicMock
    ) -> None:
        settings = MagicMock()
        settings.default_model = "default-model"
        mock_settings.return_value = settings
        mock_allowed.return_value = ["allowed-model"]

        config = {"model": "allowed-model", "model_provider_id": "   "}
        TaskService._validate_and_normalize_model(config)
        # Empty provider_id is treated as None
        self.assertNotIn("model_provider_id", config)


class TestTaskServiceNormalizeMemoryEnabled(unittest.TestCase):
    """Test _normalize_memory_enabled static method."""

    @patch("app.services.task_service.get_settings")
    def test_non_dict_config(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = True
        # Should not raise
        TaskService._normalize_memory_enabled("not a dict")  # type: ignore

    @patch("app.services.task_service.get_settings")
    def test_no_memory_enabled_key(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = True
        config = {"other": "value"}
        TaskService._normalize_memory_enabled(config)
        self.assertEqual(config.get("memory_enabled"), False)

    @patch("app.services.task_service.get_settings")
    def test_memory_enabled_true(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = True
        config = {"memory_enabled": True}
        TaskService._normalize_memory_enabled(config)
        self.assertTrue(config["memory_enabled"])

    @patch("app.services.task_service.get_settings")
    def test_memory_enabled_false(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = True
        config = {"memory_enabled": False}
        TaskService._normalize_memory_enabled(config)
        self.assertFalse(config["memory_enabled"])

    @patch("app.services.task_service.get_settings")
    def test_memory_enabled_invalid_type(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = True
        config = {"memory_enabled": 123}
        with self.assertRaises(AppException) as ctx:
            TaskService._normalize_memory_enabled(config)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    @patch("app.services.task_service.get_settings")
    def test_memory_disabled_globally(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.mem0_enabled = False
        config = {"memory_enabled": True}
        TaskService._normalize_memory_enabled(config)
        self.assertFalse(config["memory_enabled"])


class TestTaskServiceApplyProjectRepoDefaults(unittest.TestCase):
    """Test _apply_project_repo_defaults static method."""

    def test_config_none(self) -> None:
        project = MagicMock()
        result = TaskService._apply_project_repo_defaults(None, project)
        self.assertIsNone(result)

    def test_config_without_repo_url(self) -> None:
        config = {"other": "value"}
        project = MagicMock()
        project.repo_url = "https://github.com/test/repo"
        result = TaskService._apply_project_repo_defaults(config, project)
        self.assertEqual(result["repo_url"], "https://github.com/test/repo")

    def test_config_with_repo_url(self) -> None:
        config = {"repo_url": "https://github.com/override/repo"}
        project = MagicMock()
        project.repo_url = "https://github.com/test/repo"
        result = TaskService._apply_project_repo_defaults(config, project)
        # Config repo_url should take precedence
        self.assertEqual(result["repo_url"], "https://github.com/override/repo")


class TestTaskServiceNormalizeScheduledAt(unittest.TestCase):
    """Test _normalize_scheduled_at instance method."""

    def test_naive_datetime_with_no_timezone(self) -> None:
        service = TaskService()
        dt = datetime(2024, 1, 15, 10, 30, 0)  # naive datetime
        result = service._normalize_scheduled_at(dt, None)
        # Should be converted to UTC
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_naive_datetime_with_timezone(self) -> None:
        from datetime import timedelta

        service = TaskService()
        dt = datetime(2024, 1, 15, 10, 30, 0)  # naive datetime
        # Mock ZoneInfo to return a valid timezone object
        with patch("app.services.task_service.ZoneInfo") as mock_zoneinfo:
            # Create a real timezone with offset for testing
            mock_tz = timezone(timedelta(hours=5))  # UTC+5
            mock_zoneinfo.return_value = mock_tz
            result = service._normalize_scheduled_at(dt, "Some/Timezone")
            # Should be converted to UTC (10:30 UTC+5 becomes 05:30 UTC)
            self.assertEqual(result.tzinfo, timezone.utc)
            mock_zoneinfo.assert_called_once_with("Some/Timezone")

    def test_aware_datetime(self) -> None:
        service = TaskService()
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = service._normalize_scheduled_at(dt, "America/New_York")
        # Already aware, timezone param ignored
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_invalid_timezone(self) -> None:
        service = TaskService()
        dt = datetime(2024, 1, 15, 10, 30, 0)
        with self.assertRaises(AppException) as ctx:
            service._normalize_scheduled_at(dt, "Invalid/Timezone")
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestTaskServiceNormalizeMcpServerIds(unittest.TestCase):
    """Test _normalize_mcp_server_ids static method."""

    def test_none_value(self) -> None:
        result = TaskService._normalize_mcp_server_ids(None)
        self.assertIsNone(result)

    def test_list_of_ints(self) -> None:
        result = TaskService._normalize_mcp_server_ids([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_list_with_non_ints(self) -> None:
        result = TaskService._normalize_mcp_server_ids([1, "invalid", 3])
        self.assertEqual(result, [1, 3])

    def test_non_list_value(self) -> None:
        result = TaskService._normalize_mcp_server_ids("not a list")
        self.assertIsNone(result)

    def test_empty_list(self) -> None:
        result = TaskService._normalize_mcp_server_ids([])
        self.assertEqual(result, [])


class TestTaskServiceNormalizeSkillIds(unittest.TestCase):
    """Test _normalize_skill_ids static method."""

    def test_none_value(self) -> None:
        result = TaskService._normalize_skill_ids(None)
        self.assertIsNone(result)

    def test_list_of_ints(self) -> None:
        result = TaskService._normalize_skill_ids([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_list_with_non_ints(self) -> None:
        result = TaskService._normalize_skill_ids([1, "invalid", 3])
        self.assertEqual(result, [1, 3])


class TestTaskServiceNormalizeSubagentIds(unittest.TestCase):
    """Test _normalize_subagent_ids static method."""

    def test_none_value(self) -> None:
        result = TaskService._normalize_subagent_ids(None)
        self.assertIsNone(result)

    def test_list_of_ints(self) -> None:
        result = TaskService._normalize_subagent_ids([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_list_with_non_ints(self) -> None:
        result = TaskService._normalize_subagent_ids([1, "invalid", 3])
        self.assertEqual(result, [1, 3])


class TestTaskServiceNormalizePluginIds(unittest.TestCase):
    """Test _normalize_plugin_ids static method."""

    def test_none_value(self) -> None:
        result = TaskService._normalize_plugin_ids(None)
        self.assertIsNone(result)

    def test_list_of_ints(self) -> None:
        result = TaskService._normalize_plugin_ids([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_list_with_non_ints(self) -> None:
        result = TaskService._normalize_plugin_ids([1, "invalid", 3])
        self.assertEqual(result, [1, 3])


class TestTaskServiceMergeConfigMap(unittest.TestCase):
    """Test _merge_config_map static method."""

    def test_empty_defaults(self) -> None:
        defaults = {}
        overrides = {"key": "value"}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertEqual(result, {"key": "value"})

    def test_empty_overrides(self) -> None:
        defaults = {"key": "value"}
        overrides = {}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertEqual(result, {"key": "value"})

    def test_override_takes_precedence(self) -> None:
        defaults = {"key": "default"}
        overrides = {"key": "override"}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertEqual(result, {"key": "override"})

    def test_both_contribute(self) -> None:
        defaults = {"key1": "default"}
        overrides = {"key2": "override"}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertEqual(result, {"key1": "default", "key2": "override"})


class TestTaskServiceBuildUserMcpServerIdsDefaults(unittest.TestCase):
    """Test _build_user_mcp_server_ids_defaults instance method."""

    def test_empty_list(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserMcpInstallRepository") as mock_repo:
            mock_repo.list_by_user.return_value = []
            result = service._build_user_mcp_server_ids_defaults(db, "user-123")
            self.assertEqual(result, [])

    def test_with_installs(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserMcpInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.server_id = 1
            install1.enabled = True
            install2 = MagicMock()
            install2.server_id = 2
            install2.enabled = False
            mock_repo.list_by_user.return_value = [install1, install2]

            result = service._build_user_mcp_server_ids_defaults(db, "user-123")
            self.assertEqual(result, [1])


class TestTaskServiceBuildUserSkillIdsDefaults(unittest.TestCase):
    """Test _build_user_skill_ids_defaults instance method."""

    def test_empty_list(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserSkillInstallRepository") as mock_repo:
            mock_repo.list_by_user.return_value = []
            result = service._build_user_skill_ids_defaults(db, "user-123")
            self.assertEqual(result, [])

    def test_with_installs(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserSkillInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.skill_id = 1
            install1.enabled = True
            mock_repo.list_by_user.return_value = [install1]

            result = service._build_user_skill_ids_defaults(db, "user-123")
            self.assertEqual(result, [1])


class TestTaskServiceBuildUserPluginIdsDefaults(unittest.TestCase):
    """Test _build_user_plugin_ids_defaults instance method."""

    def test_empty_list(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch(
            "app.services.task_service.UserPluginInstallRepository"
        ) as mock_repo:
            mock_repo.list_by_user.return_value = []
            result = service._build_user_plugin_ids_defaults(db, "user-123")
            self.assertEqual(result, [])

    def test_with_installs(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch(
            "app.services.task_service.UserPluginInstallRepository"
        ) as mock_repo:
            install1 = MagicMock()
            install1.plugin_id = 1
            install1.enabled = True
            mock_repo.list_by_user.return_value = [install1]

            result = service._build_user_plugin_ids_defaults(db, "user-123")
            self.assertEqual(result, [1])


class TestTaskServiceBuildConfigSnapshot(unittest.TestCase):
    """Test _build_config_snapshot instance method."""

    def test_none_task_config(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch.object(
            service, "_build_user_mcp_server_ids_defaults", return_value=[]
        ):
            with patch.object(
                service, "_build_user_skill_ids_defaults", return_value=[]
            ):
                with patch.object(
                    service, "_build_user_plugin_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_subagent_ids_defaults", return_value=[]
                    ):
                        result = service._build_config_snapshot(
                            db, "user-123", None, base_config={}
                        )
                        self.assertIn("mcp_server_ids", result)
                        self.assertIn("skill_ids", result)
                        self.assertIn("plugin_ids", result)

    def test_base_config_pop_legacy_fields(self) -> None:
        db = MagicMock()
        service = TaskService()
        base_config = {
            "mcp_config": {"servers": {}},
            "skill_files": ["file1"],
            "plugin_files": ["file2"],
            "input_files": ["file3"],
        }
        with patch.object(
            service, "_build_user_mcp_server_ids_defaults", return_value=[]
        ):
            with patch.object(
                service, "_build_user_skill_ids_defaults", return_value=[]
            ):
                with patch.object(
                    service, "_build_user_plugin_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_subagent_ids_defaults", return_value=[]
                    ):
                        result = service._build_config_snapshot(
                            db, "user-123", None, base_config=base_config
                        )
                        # Legacy fields should be removed
                        self.assertNotIn("mcp_config", result)
                        self.assertNotIn("skill_files", result)
                        self.assertNotIn("plugin_files", result)
                        self.assertNotIn("input_files", result)

    def test_with_task_config(self) -> None:
        from app.schemas.task import TaskConfig

        db = MagicMock()
        service = TaskService()
        task_config = TaskConfig(model="test-model")
        with patch.object(
            service, "_build_user_mcp_server_ids_defaults", return_value=[]
        ):
            with patch.object(
                service, "_build_user_skill_ids_defaults", return_value=[]
            ):
                with patch.object(
                    service, "_build_user_plugin_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_subagent_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service, "_validate_and_normalize_model"
                        ) as mock_validate:
                            result = service._build_config_snapshot(
                                db, "user-123", task_config, base_config={}
                            )
                            mock_validate.assert_called_once()
                            self.assertIn("model", result)

    def test_with_mcp_toggles(self) -> None:
        db = MagicMock()
        service = TaskService()
        task_config = MagicMock()
        task_config.model_dump.return_value = {
            "model": "test-model",
            "mcp_config": {"server1": True},
        }
        with patch(
            "app.services.task_service.get_allowed_model_ids",
            return_value=["test-model"],
        ):
            with patch("app.services.task_service.get_settings") as mock_settings:
                mock_settings.return_value.default_model = "default-model"
                with patch.object(
                    service,
                    "_build_user_mcp_server_ids_with_toggles",
                    return_value=[1, 2],
                ):
                    with patch.object(
                        service, "_build_user_skill_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service, "_build_user_plugin_ids_defaults", return_value=[]
                        ):
                            with patch.object(
                                service,
                                "_build_user_subagent_ids_defaults",
                                return_value=[],
                            ):
                                result = service._build_config_snapshot(
                                    db, "user-123", task_config, base_config={}
                                )
                                self.assertEqual(result["mcp_server_ids"], [1, 2])

    def test_base_mcp_server_ids_not_none(self) -> None:
        db = MagicMock()
        service = TaskService()
        base_config = {"mcp_server_ids": [10, 20]}
        with patch(
            "app.services.task_service.get_allowed_model_ids",
            return_value=["test-model"],
        ):
            with patch("app.services.task_service.get_settings") as mock_settings:
                mock_settings.return_value.default_model = "default-model"
                with patch.object(
                    service, "_build_user_skill_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_plugin_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service,
                            "_build_user_subagent_ids_defaults",
                            return_value=[],
                        ):
                            result = service._build_config_snapshot(
                                db, "user-123", None, base_config=base_config
                            )
                            self.assertEqual(result["mcp_server_ids"], [10, 20])

    def test_base_skill_ids_not_none(self) -> None:
        db = MagicMock()
        service = TaskService()
        base_config = {"skill_ids": [30, 40]}
        with patch(
            "app.services.task_service.get_allowed_model_ids",
            return_value=["test-model"],
        ):
            with patch("app.services.task_service.get_settings") as mock_settings:
                mock_settings.return_value.default_model = "default-model"
                with patch.object(
                    service, "_build_user_mcp_server_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_plugin_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service,
                            "_build_user_subagent_ids_defaults",
                            return_value=[],
                        ):
                            result = service._build_config_snapshot(
                                db, "user-123", None, base_config=base_config
                            )
                            self.assertEqual(result["skill_ids"], [30, 40])

    def test_base_plugin_ids_not_none(self) -> None:
        db = MagicMock()
        service = TaskService()
        base_config = {"plugin_ids": [50, 60]}
        with patch(
            "app.services.task_service.get_allowed_model_ids",
            return_value=["test-model"],
        ):
            with patch("app.services.task_service.get_settings") as mock_settings:
                mock_settings.return_value.default_model = "default-model"
                with patch.object(
                    service, "_build_user_mcp_server_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_skill_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service,
                            "_build_user_subagent_ids_defaults",
                            return_value=[],
                        ):
                            result = service._build_config_snapshot(
                                db, "user-123", None, base_config=base_config
                            )
                            self.assertEqual(result["plugin_ids"], [50, 60])

    def test_base_subagent_ids_not_none(self) -> None:
        db = MagicMock()
        service = TaskService()
        base_config = {"subagent_ids": [70, 80]}
        with patch(
            "app.services.task_service.get_allowed_model_ids",
            return_value=["test-model"],
        ):
            with patch("app.services.task_service.get_settings") as mock_settings:
                mock_settings.return_value.default_model = "default-model"
                with patch.object(
                    service, "_build_user_mcp_server_ids_defaults", return_value=[]
                ):
                    with patch.object(
                        service, "_build_user_skill_ids_defaults", return_value=[]
                    ):
                        with patch.object(
                            service, "_build_user_plugin_ids_defaults", return_value=[]
                        ):
                            result = service._build_config_snapshot(
                                db, "user-123", None, base_config=base_config
                            )
                            self.assertEqual(result["subagent_ids"], [70, 80])


class TestTaskServiceBuildUserSubagentIdsDefaults(unittest.TestCase):
    """Test _build_user_subagent_ids_defaults instance method."""

    def test_empty_list(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.SubAgentRepository") as mock_repo:
            mock_repo.list_enabled_by_user.return_value = []
            result = service._build_user_subagent_ids_defaults(db, "user-123")
            self.assertEqual(result, [])

    def test_with_subagents(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.SubAgentRepository") as mock_repo:
            subagent1 = MagicMock()
            subagent1.id = 1
            subagent2 = MagicMock()
            subagent2.id = 2
            mock_repo.list_enabled_by_user.return_value = [subagent1, subagent2]

            result = service._build_user_subagent_ids_defaults(db, "user-123")
            self.assertEqual(result, [1, 2])


class TestTaskServiceBuildUserMcpServerIdsWithToggles(unittest.TestCase):
    """Test _build_user_mcp_server_ids_with_toggles instance method."""

    def test_with_toggles(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserMcpInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.server_id = 1
            install2 = MagicMock()
            install2.server_id = 2
            mock_repo.list_by_user.return_value = [install1, install2]

            toggles = {"1": True, "2": False}
            result = service._build_user_mcp_server_ids_with_toggles(
                db, "user-123", toggles
            )
            self.assertEqual(result, [1])

    def test_toggle_not_in_toggles_uses_enabled(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserMcpInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.server_id = 1
            install1.enabled = True
            install2 = MagicMock()
            install2.server_id = 2
            install2.enabled = False
            mock_repo.list_by_user.return_value = [install1, install2]

            # Empty toggles - should use install.enabled
            toggles: dict[str, bool] = {}
            result = service._build_user_mcp_server_ids_with_toggles(
                db, "user-123", toggles
            )
            self.assertEqual(result, [1])


class TestTaskServiceBuildUserSkillIdsWithToggles(unittest.TestCase):
    """Test _build_user_skill_ids_with_toggles instance method."""

    def test_with_toggles(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserSkillInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.skill_id = 1
            install2 = MagicMock()
            install2.skill_id = 2
            mock_repo.list_by_user.return_value = [install1, install2]

            toggles = {"1": True, "2": False}
            result = service._build_user_skill_ids_with_toggles(db, "user-123", toggles)
            self.assertEqual(result, [1])

    def test_toggle_not_in_toggles_uses_enabled(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch("app.services.task_service.UserSkillInstallRepository") as mock_repo:
            install1 = MagicMock()
            install1.skill_id = 1
            install1.enabled = True
            install2 = MagicMock()
            install2.skill_id = 2
            install2.enabled = False
            mock_repo.list_by_user.return_value = [install1, install2]

            # Empty toggles - should use install.enabled
            toggles: dict[str, bool] = {}
            result = service._build_user_skill_ids_with_toggles(db, "user-123", toggles)
            self.assertEqual(result, [1])


class TestTaskServiceBuildUserPluginIdsWithToggles(unittest.TestCase):
    """Test _build_user_plugin_ids_with_toggles instance method."""

    def test_with_toggles(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch(
            "app.services.task_service.UserPluginInstallRepository"
        ) as mock_repo:
            install1 = MagicMock()
            install1.plugin_id = 1
            install2 = MagicMock()
            install2.plugin_id = 2
            mock_repo.list_by_user.return_value = [install1, install2]

            toggles = {"1": True, "2": False}
            result = service._build_user_plugin_ids_with_toggles(
                db, "user-123", toggles
            )
            self.assertEqual(result, [1])

    def test_toggle_not_in_toggles_uses_enabled(self) -> None:
        db = MagicMock()
        service = TaskService()
        with patch(
            "app.services.task_service.UserPluginInstallRepository"
        ) as mock_repo:
            install1 = MagicMock()
            install1.plugin_id = 1
            install1.enabled = True
            install2 = MagicMock()
            install2.plugin_id = 2
            install2.enabled = False
            mock_repo.list_by_user.return_value = [install1, install2]

            # Empty toggles - should use install.enabled
            toggles: dict[str, bool] = {}
            result = service._build_user_plugin_ids_with_toggles(
                db, "user-123", toggles
            )
            self.assertEqual(result, [1])


class TestTaskServiceMergeConfigMapExtended(unittest.TestCase):
    """Extended tests for _merge_config_map static method."""

    def test_none_value_removes_key(self) -> None:
        defaults = {"key1": "value1", "key2": "value2"}
        overrides = {"key1": None}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertNotIn("key1", result)
        self.assertEqual(result["key2"], "value2")

    def test_nested_dict_merge(self) -> None:
        defaults = {"nested": {"a": 1, "b": 2}}
        overrides = {"nested": {"b": 3, "c": 4}}
        result = TaskService._merge_config_map(defaults, overrides)
        self.assertEqual(result["nested"], {"a": 1, "b": 3, "c": 4})

    def test_none_overrides(self) -> None:
        defaults = {"key": "value"}
        result = TaskService._merge_config_map(defaults, None)  # type: ignore
        self.assertEqual(result, {"key": "value"})


class TestTaskServiceValidateModelExtended(unittest.TestCase):
    """Extended tests for _validate_and_normalize_model."""

    @patch("app.services.task_service.get_allowed_model_ids")
    @patch("app.services.task_service.get_settings")
    def test_model_not_allowed_no_provider(
        self, mock_settings: MagicMock, mock_allowed: MagicMock
    ) -> None:
        """Test model not in allowed list and no provider_id (line 90-94)."""
        settings = MagicMock()
        settings.default_model = "default-model"
        mock_settings.return_value = settings
        mock_allowed.return_value = ["allowed-model"]

        config = {"model": "unknown-model"}
        with self.assertRaises(AppException) as ctx:
            TaskService._validate_and_normalize_model(config)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("Invalid model", str(ctx.exception.message))

    @patch("app.services.task_service.infer_provider_id")
    @patch("app.services.task_service.get_allowed_model_ids")
    @patch("app.services.task_service.get_settings")
    def test_model_with_inferred_provider(
        self, mock_settings: MagicMock, mock_allowed: MagicMock, mock_infer: MagicMock
    ) -> None:
        """Test model with inferred provider_id (line 98-99)."""
        settings = MagicMock()
        settings.default_model = "default-model"
        mock_settings.return_value = settings
        mock_allowed.return_value = []
        mock_infer.return_value = "anthropic"

        config = {"model": "claude-3-opus"}
        TaskService._validate_and_normalize_model(config)
        self.assertEqual(config["model"], "claude-3-opus")
        self.assertEqual(config["model_provider_id"], "anthropic")


class TestTaskServiceApplyProjectRepoDefaultsExtended(unittest.TestCase):
    """Extended tests for _apply_project_repo_defaults."""

    def test_project_none(self) -> None:
        """Test with None project."""
        config = {"key": "value"}
        result = TaskService._apply_project_repo_defaults(config, None)
        self.assertEqual(result, {"key": "value"})

    def test_project_no_repo_url(self) -> None:
        """Test project with empty repo_url (line 140)."""
        config = {"other": "value"}
        project = MagicMock()
        project.repo_url = ""
        result = TaskService._apply_project_repo_defaults(config, project)
        self.assertNotIn("repo_url", result)

    def test_config_explicit_empty_repo_url(self) -> None:
        """Test explicit empty repo_url in config (line 162-163)."""
        config = {"repo_url": ""}
        project = MagicMock()
        project.repo_url = "https://github.com/test/repo"
        result = TaskService._apply_project_repo_defaults(config, project)
        self.assertEqual(result["repo_url"], "")

    def test_config_same_repo_url_fills_branch(self) -> None:
        """Test same repo_url fills branch/token (line 167-175)."""
        config = {"repo_url": "https://github.com/test/repo"}
        project = MagicMock()
        project.repo_url = "https://github.com/test/repo"
        project.git_branch = "main"
        project.git_token_env_key = "GIT_TOKEN"
        result = TaskService._apply_project_repo_defaults(config, project)
        self.assertEqual(result["git_branch"], "main")
        self.assertEqual(result["git_token_env_key"], "GIT_TOKEN")

    def test_config_different_repo_url_no_fill(self) -> None:
        """Test different repo_url doesn't fill defaults."""
        config = {"repo_url": "https://github.com/other/repo"}
        project = MagicMock()
        project.repo_url = "https://github.com/test/repo"
        project.git_branch = "main"
        project.git_token_env_key = "GIT_TOKEN"
        result = TaskService._apply_project_repo_defaults(config, project)
        self.assertNotIn("git_branch", result)


class TestTaskServiceEnqueueTask(unittest.TestCase):
    """Test enqueue_task method."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = TaskService()
        self.user_id = "user-123"

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_empty_prompt(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with empty prompt raises error (line 248-253)."""
        request = MagicMock()
        request.prompt = "   "
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = None
        request.session_id = None
        request.permission_mode = "default"
        request.config = None
        request.client_request_id = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("empty", ctx.exception.message.lower())

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_invalid_permission_mode(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with invalid permission_mode (line 258-267)."""
        request = MagicMock()
        request.prompt = "test prompt"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = None
        request.session_id = None
        request.permission_mode = "invalid_mode"
        request.config = None
        request.client_request_id = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)
        self.assertIn("Invalid permission_mode", ctx.exception.message)

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_project_not_found(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with project not found (line 273-278)."""
        request = MagicMock()
        request.prompt = "test prompt"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = uuid.uuid4()
        request.session_id = None
        request.permission_mode = "default"
        request.config = None
        request.client_request_id = None

        mock_project_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_session_not_found(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with session not found (line 284-288)."""
        request = MagicMock()
        request.prompt = "test prompt"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = None
        request.session_id = uuid.uuid4()
        request.permission_mode = "default"
        request.config = None
        request.client_request_id = None

        mock_session_repo.get_by_id_for_update.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_session_wrong_user(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with session wrong user (line 289-293)."""
        request = MagicMock()
        request.prompt = "test prompt"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = None
        request.session_id = uuid.uuid4()
        request.permission_mode = "default"
        request.config = None
        request.client_request_id = None

        mock_session = MagicMock()
        mock_session.user_id = "other-user"
        mock_session_repo.get_by_id_for_update.return_value = mock_session

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.ProjectRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_project_session_mismatch(
        self,
        mock_queue_service: MagicMock,
        mock_project_repo: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        """Test enqueue_task with project_id/session_id mismatch (line 294-298)."""
        project_id = uuid.uuid4()
        session_id = uuid.uuid4()
        request = MagicMock()
        request.prompt = "test prompt"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.project_id = project_id
        request.session_id = session_id
        request.permission_mode = "default"
        request.config = None
        request.client_request_id = None

        mock_session = MagicMock()
        mock_session.user_id = self.user_id
        mock_session.project_id = uuid.uuid4()  # Different project
        mock_session_repo.get_by_id_for_update.return_value = mock_session

        # Project lookup fails because session's project is different
        mock_project_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.enqueue_task(self.db, self.user_id, request)
        # The error is PROJECT_NOT_FOUND because project_repo.get_by_id returns None
        self.assertEqual(ctx.exception.error_code, ErrorCode.PROJECT_NOT_FOUND)


class TestTaskServiceInternalTaskMethods(unittest.TestCase):
    """Test manager-facing internal task helpers."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = TaskService()
        self.user_id = "user-123"

    @patch("app.services.task_service.SessionRepository")
    @patch("app.services.task_service.SessionQueueService")
    def test_enqueue_task_from_manager_new_session(
        self,
        mock_queue_service_cls: MagicMock,
        mock_session_repo: MagicMock,
    ) -> None:
        request = MagicMock()
        request.prompt = "run from manager"
        request.schedule_mode = "immediate"
        request.scheduled_at = None
        request.timezone = None
        request.permission_mode = "default"
        request.config_snapshot = {
            "container_mode": "persistent",
            "browser_enabled": True,
        }
        request.session_id = None
        request.client_request_id = None

        mock_queue_service = MagicMock()
        mock_queue_service_cls.return_value = mock_queue_service
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        mock_session_repo.create.return_value = mock_session

        expected = MagicMock()
        expected.session_id = mock_session.id
        expected.accepted_type = "run"
        expected.status = "queued"
        mock_queue_service.count_active_items.return_value = 0

        with patch.object(
            self.service,
            "_enqueue_or_materialize",
            return_value=expected,
        ) as mock_enqueue:
            result = self.service.enqueue_task_from_manager(
                self.db,
                self.user_id,
                request,
            )

            assert result is expected
            mock_session_repo.create.assert_called_once()
            mock_enqueue.assert_called_once()

    @patch("app.services.task_service.RunRepository")
    def test_get_internal_task_status_for_run(self, mock_run_repo: MagicMock) -> None:
        run_id = uuid.uuid4()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.session_id = session_id
        mock_run.status = "queued"
        mock_run_repo.get_by_id.return_value = mock_run

        result = self.service.get_internal_task_status(self.db, run_id)

        assert result.task_id == run_id
        assert result.task_type == "run"
        assert result.session_id == session_id
        assert result.run_id == run_id

    @patch("app.services.task_service.SessionQueueItemRepository")
    @patch("app.services.task_service.RunRepository")
    def test_get_internal_task_status_for_queue_item(
        self,
        mock_run_repo: MagicMock,
        mock_queue_repo: MagicMock,
    ) -> None:
        task_id = uuid.uuid4()
        session_id = uuid.uuid4()
        mock_run_repo.get_by_id.return_value = None
        queue_item = MagicMock()
        queue_item.id = task_id
        queue_item.session_id = session_id
        queue_item.status = "queued"
        mock_queue_repo.get_by_id.return_value = queue_item

        result = self.service.get_internal_task_status(self.db, task_id)

        assert result.task_type == "queued_query"
        assert result.queue_item_id == task_id
        assert result.session_id == session_id


if __name__ == "__main__":
    unittest.main()
