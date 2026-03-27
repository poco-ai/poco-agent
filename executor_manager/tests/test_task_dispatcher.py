import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.task_dispatcher import TaskDispatcher, _extract_enabled_skill_names


class TestExtractEnabledSkillNames(unittest.TestCase):
    """Test _extract_enabled_skill_names helper function."""

    def test_empty_dict(self) -> None:
        result = _extract_enabled_skill_names({})
        assert result == []

    def test_non_dict_input(self) -> None:
        result = _extract_enabled_skill_names("not a dict")
        assert result == []

    def test_none_input(self) -> None:
        result = _extract_enabled_skill_names(None)
        assert result == []

    def test_single_skill_enabled(self) -> None:
        skills = {"skill1": {"enabled": True}}
        result = _extract_enabled_skill_names(skills)
        assert result == ["skill1"]

    def test_single_skill_no_enabled_field(self) -> None:
        skills = {"skill1": {}}
        result = _extract_enabled_skill_names(skills)
        assert result == ["skill1"]

    def test_skill_disabled(self) -> None:
        skills = {"skill1": {"enabled": False}}
        result = _extract_enabled_skill_names(skills)
        assert result == []

    def test_multiple_skills_mixed(self) -> None:
        skills = {
            "zebra": {"enabled": True},
            "alpha": {"enabled": True},
            "beta": {"enabled": False},
            "gamma": {},
        }
        result = _extract_enabled_skill_names(skills)
        # Should be sorted
        assert result == ["alpha", "gamma", "zebra"]

    def test_non_string_skill_name(self) -> None:
        skills = {123: {"enabled": True}}
        result = _extract_enabled_skill_names(skills)
        assert result == []

    def test_empty_skill_name(self) -> None:
        skills = {"": {"enabled": True}, "  ": {"enabled": True}}
        result = _extract_enabled_skill_names(skills)
        assert result == []

    def test_skill_name_with_whitespace(self) -> None:
        skills = {"  skill1  ": {"enabled": True}}
        result = _extract_enabled_skill_names(skills)
        assert result == ["skill1"]

    def test_non_dict_spec(self) -> None:
        skills = {"skill1": "not a dict"}
        result = _extract_enabled_skill_names(skills)
        assert result == ["skill1"]

    def test_enabled_is_not_false(self) -> None:
        skills = {"skill1": {"enabled": "true"}}
        result = _extract_enabled_skill_names(skills)
        assert result == ["skill1"]


class TestTaskDispatcherGetContainerPool(unittest.TestCase):
    """Test TaskDispatcher.get_container_pool."""

    def test_creates_pool_if_none(self) -> None:
        # Reset class variable
        TaskDispatcher.container_pool = None

        with patch("app.scheduler.task_dispatcher.ContainerPool") as mock_pool_cls:
            mock_pool = MagicMock()
            mock_pool_cls.return_value = mock_pool

            result = TaskDispatcher.get_container_pool()

            assert result == mock_pool
            mock_pool_cls.assert_called_once()

        # Clean up
        TaskDispatcher.container_pool = None

    def test_returns_existing_pool(self) -> None:
        mock_pool = MagicMock()
        TaskDispatcher.container_pool = mock_pool

        result = TaskDispatcher.get_container_pool()

        assert result == mock_pool

        # Clean up
        TaskDispatcher.container_pool = None


@pytest.mark.asyncio
class TestTaskDispatcherResolveExecutorTarget:
    """Test TaskDispatcher.resolve_executor_target."""

    async def test_resolve_executor_target(self) -> None:
        TaskDispatcher.container_pool = None

        mock_pool = MagicMock()
        mock_pool.get_or_create_container = AsyncMock(
            return_value=("http://executor:8080", "container-123")
        )

        with patch(
            "app.scheduler.task_dispatcher.ContainerPool",
            return_value=mock_pool,
        ):
            TaskDispatcher.container_pool = mock_pool

            result = await TaskDispatcher.resolve_executor_target(
                session_id="session-123",
                user_id="user-456",
                browser_enabled=True,
                container_mode="ephemeral",
                container_id=None,
            )

            assert result == ("http://executor:8080", "container-123")
            mock_pool.get_or_create_container.assert_called_once_with(
                session_id="session-123",
                user_id="user-456",
                browser_enabled=True,
                container_mode="ephemeral",
                container_id=None,
            )

        # Clean up
        TaskDispatcher.container_pool = None


@pytest.mark.asyncio
class TestTaskDispatcherOnTaskComplete:
    """Test TaskDispatcher.on_task_complete."""

    async def test_on_task_complete(self) -> None:
        mock_pool = MagicMock()
        mock_pool.on_task_complete = AsyncMock()

        TaskDispatcher.container_pool = mock_pool

        await TaskDispatcher.on_task_complete("session-123")

        mock_pool.on_task_complete.assert_called_once_with("session-123")

        # Clean up
        TaskDispatcher.container_pool = None


@pytest.mark.asyncio
class TestTaskDispatcherDispatch:
    """Test TaskDispatcher.dispatch."""

    def setUp(self) -> None:
        TaskDispatcher.container_pool = None

    async def test_dispatch_empty_callback_url(self) -> None:
        """Test dispatch raises ValueError when callback_base_url is empty."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = ""
            mock_settings_obj.callback_token = "token"
            mock_settings.return_value = mock_settings_obj

            # Mock all dependencies that are created before the check
            with patch("app.scheduler.task_dispatcher.ExecutorClient"):
                with patch("app.scheduler.task_dispatcher.BackendClient"):
                    with patch("app.scheduler.task_dispatcher.ConfigResolver"):
                        with patch("app.scheduler.task_dispatcher.SkillStager"):
                            with patch("app.scheduler.task_dispatcher.PluginStager"):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager"
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager"
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager"
                                        ):
                                            with pytest.raises(
                                                ValueError,
                                                match="callback_base_url cannot be empty",
                                            ):
                                                await TaskDispatcher.dispatch(
                                                    task_id="task-123",
                                                    session_id="session-456",
                                                    prompt="Hello",
                                                    config={"user_id": "user-789"},
                                                )

    async def test_dispatch_success(self) -> None:
        """Test successful dispatch flow."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = "http://callback"
            mock_settings_obj.callback_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            # Mock all dependencies
            mock_executor_client = MagicMock()
            mock_executor_client.execute_task = AsyncMock()

            mock_backend_client = MagicMock()
            mock_backend_client.resolve_slash_commands = AsyncMock(return_value={})
            mock_backend_client.update_session_status = AsyncMock()

            mock_config_resolver = MagicMock()
            mock_config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {"skill1": {"content": "skill"}},
                    "plugin_files": {"plugin1": {"content": "plugin"}},
                    "input_files": [{"path": "/tmp/file.txt"}],
                    "browser_enabled": False,
                }
            )

            mock_skill_stager = MagicMock()
            mock_skill_stager.stage_skills = MagicMock(
                return_value={"skill1": {"staged": True}}
            )

            mock_plugin_stager = MagicMock()
            mock_plugin_stager.stage_plugins = MagicMock(
                return_value={"plugin1": {"staged": True}}
            )

            mock_attachment_stager = MagicMock()
            mock_attachment_stager.stage_inputs = MagicMock(
                return_value=[{"staged": True}]
            )

            mock_slash_command_stager = MagicMock()
            mock_slash_command_stager.stage_commands = MagicMock(return_value={})

            mock_subagent_stager = MagicMock()
            mock_subagent_stager.stage_raw_agents = MagicMock(return_value={})

            with patch(
                "app.scheduler.task_dispatcher.ExecutorClient",
                return_value=mock_executor_client,
            ):
                with patch(
                    "app.scheduler.task_dispatcher.BackendClient",
                    return_value=mock_backend_client,
                ):
                    with patch(
                        "app.scheduler.task_dispatcher.ConfigResolver",
                        return_value=mock_config_resolver,
                    ):
                        with patch(
                            "app.scheduler.task_dispatcher.SkillStager",
                            return_value=mock_skill_stager,
                        ):
                            with patch(
                                "app.scheduler.task_dispatcher.PluginStager",
                                return_value=mock_plugin_stager,
                            ):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager",
                                    return_value=mock_attachment_stager,
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager",
                                        return_value=mock_slash_command_stager,
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager",
                                            return_value=mock_subagent_stager,
                                        ):
                                            with patch.object(
                                                TaskDispatcher,
                                                "resolve_executor_target",
                                                AsyncMock(
                                                    return_value=(
                                                        "http://executor:8080",
                                                        "container-123",
                                                    )
                                                ),
                                            ):
                                                await TaskDispatcher.dispatch(
                                                    task_id="task-123",
                                                    session_id="session-456",
                                                    prompt="Hello",
                                                    config={"user_id": "user-789"},
                                                )

                                                mock_executor_client.execute_task.assert_called_once()
                                                mock_backend_client.update_session_status.assert_called_once_with(
                                                    "session-456", "running"
                                                )

    async def test_dispatch_with_exception(self) -> None:
        """Test dispatch handles exception and updates session status."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = "http://callback"
            mock_settings_obj.callback_token = "token"
            mock_settings.return_value = mock_settings_obj

            mock_executor_client = MagicMock()
            mock_executor_client.execute_task = AsyncMock(
                side_effect=RuntimeError("Executor failed")
            )

            mock_backend_client = MagicMock()
            mock_backend_client.resolve_slash_commands = AsyncMock(return_value={})
            mock_backend_client.update_session_status = AsyncMock()

            mock_config_resolver = MagicMock()
            mock_config_resolver.resolve = AsyncMock(return_value={})

            mock_skill_stager = MagicMock()
            mock_skill_stager.stage_skills = MagicMock(return_value={})

            mock_plugin_stager = MagicMock()
            mock_plugin_stager.stage_plugins = MagicMock(return_value={})

            mock_attachment_stager = MagicMock()
            mock_attachment_stager.stage_inputs = MagicMock(return_value=[])

            mock_slash_command_stager = MagicMock()
            mock_slash_command_stager.stage_commands = MagicMock(return_value={})

            mock_subagent_stager = MagicMock()
            mock_subagent_stager.stage_raw_agents = MagicMock(return_value={})

            mock_pool = MagicMock()
            mock_pool.cancel_task = AsyncMock()

            with patch(
                "app.scheduler.task_dispatcher.ExecutorClient",
                return_value=mock_executor_client,
            ):
                with patch(
                    "app.scheduler.task_dispatcher.BackendClient",
                    return_value=mock_backend_client,
                ):
                    with patch(
                        "app.scheduler.task_dispatcher.ConfigResolver",
                        return_value=mock_config_resolver,
                    ):
                        with patch(
                            "app.scheduler.task_dispatcher.SkillStager",
                            return_value=mock_skill_stager,
                        ):
                            with patch(
                                "app.scheduler.task_dispatcher.PluginStager",
                                return_value=mock_plugin_stager,
                            ):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager",
                                    return_value=mock_attachment_stager,
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager",
                                        return_value=mock_slash_command_stager,
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager",
                                            return_value=mock_subagent_stager,
                                        ):
                                            with patch.object(
                                                TaskDispatcher,
                                                "get_container_pool",
                                                return_value=mock_pool,
                                            ):
                                                with patch.object(
                                                    TaskDispatcher,
                                                    "resolve_executor_target",
                                                    AsyncMock(
                                                        return_value=(
                                                            "http://executor:8080",
                                                            "container-123",
                                                        )
                                                    ),
                                                ):
                                                    with pytest.raises(
                                                        RuntimeError,
                                                        match="Executor failed",
                                                    ):
                                                        await TaskDispatcher.dispatch(
                                                            task_id="task-123",
                                                            session_id="session-456",
                                                            prompt="Hello",
                                                            config={
                                                                "user_id": "user-789"
                                                            },
                                                        )

                                                    mock_backend_client.update_session_status.assert_called_with(
                                                        "session-456", "failed"
                                                    )
                                                    mock_pool.cancel_task.assert_called_once_with(
                                                        "session-456"
                                                    )

    async def test_dispatch_with_sdk_session_id(self) -> None:
        """Test dispatch with sdk_session_id parameter."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = "http://callback"
            mock_settings_obj.callback_token = "token"
            mock_settings.return_value = mock_settings_obj

            mock_executor_client = MagicMock()
            mock_executor_client.execute_task = AsyncMock()

            mock_backend_client = MagicMock()
            mock_backend_client.resolve_slash_commands = AsyncMock(return_value={})
            mock_backend_client.update_session_status = AsyncMock()

            mock_config_resolver = MagicMock()
            mock_config_resolver.resolve = AsyncMock(return_value={})

            mock_skill_stager = MagicMock()
            mock_skill_stager.stage_skills = MagicMock(return_value={})

            mock_plugin_stager = MagicMock()
            mock_plugin_stager.stage_plugins = MagicMock(return_value={})

            mock_attachment_stager = MagicMock()
            mock_attachment_stager.stage_inputs = MagicMock(return_value=[])

            mock_slash_command_stager = MagicMock()
            mock_slash_command_stager.stage_commands = MagicMock(return_value={})

            mock_subagent_stager = MagicMock()
            mock_subagent_stager.stage_raw_agents = MagicMock(return_value={})

            with patch(
                "app.scheduler.task_dispatcher.ExecutorClient",
                return_value=mock_executor_client,
            ):
                with patch(
                    "app.scheduler.task_dispatcher.BackendClient",
                    return_value=mock_backend_client,
                ):
                    with patch(
                        "app.scheduler.task_dispatcher.ConfigResolver",
                        return_value=mock_config_resolver,
                    ):
                        with patch(
                            "app.scheduler.task_dispatcher.SkillStager",
                            return_value=mock_skill_stager,
                        ):
                            with patch(
                                "app.scheduler.task_dispatcher.PluginStager",
                                return_value=mock_plugin_stager,
                            ):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager",
                                    return_value=mock_attachment_stager,
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager",
                                        return_value=mock_slash_command_stager,
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager",
                                            return_value=mock_subagent_stager,
                                        ):
                                            with patch.object(
                                                TaskDispatcher,
                                                "resolve_executor_target",
                                                AsyncMock(
                                                    return_value=(
                                                        "http://executor:8080",
                                                        "container-123",
                                                    )
                                                ),
                                            ):
                                                await TaskDispatcher.dispatch(
                                                    task_id="task-123",
                                                    session_id="session-456",
                                                    prompt="Hello",
                                                    config={"user_id": "user-789"},
                                                    sdk_session_id="sdk-session-789",
                                                )

                                                call_kwargs = mock_executor_client.execute_task.call_args.kwargs
                                                assert (
                                                    call_kwargs["sdk_session_id"]
                                                    == "sdk-session-789"
                                                )

    async def test_dispatch_with_timing_logs(self) -> None:
        """Test dispatch logs timing information when enqueued_at is provided."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = "http://callback"
            mock_settings_obj.callback_token = "token"
            mock_settings.return_value = mock_settings_obj

            mock_executor_client = MagicMock()
            mock_executor_client.execute_task = AsyncMock()

            mock_backend_client = MagicMock()
            mock_backend_client.resolve_slash_commands = AsyncMock(return_value={})
            mock_backend_client.update_session_status = AsyncMock()

            mock_config_resolver = MagicMock()
            mock_config_resolver.resolve = AsyncMock(return_value={})

            mock_skill_stager = MagicMock()
            mock_skill_stager.stage_skills = MagicMock(return_value={})

            mock_plugin_stager = MagicMock()
            mock_plugin_stager.stage_plugins = MagicMock(return_value={})

            mock_attachment_stager = MagicMock()
            mock_attachment_stager.stage_inputs = MagicMock(return_value=[])

            mock_slash_command_stager = MagicMock()
            mock_slash_command_stager.stage_commands = MagicMock(return_value={})

            mock_subagent_stager = MagicMock()
            mock_subagent_stager.stage_raw_agents = MagicMock(return_value={})

            with patch(
                "app.scheduler.task_dispatcher.ExecutorClient",
                return_value=mock_executor_client,
            ):
                with patch(
                    "app.scheduler.task_dispatcher.BackendClient",
                    return_value=mock_backend_client,
                ):
                    with patch(
                        "app.scheduler.task_dispatcher.ConfigResolver",
                        return_value=mock_config_resolver,
                    ):
                        with patch(
                            "app.scheduler.task_dispatcher.SkillStager",
                            return_value=mock_skill_stager,
                        ):
                            with patch(
                                "app.scheduler.task_dispatcher.PluginStager",
                                return_value=mock_plugin_stager,
                            ):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager",
                                    return_value=mock_attachment_stager,
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager",
                                        return_value=mock_slash_command_stager,
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager",
                                            return_value=mock_subagent_stager,
                                        ):
                                            with patch.object(
                                                TaskDispatcher,
                                                "resolve_executor_target",
                                                AsyncMock(
                                                    return_value=(
                                                        "http://executor:8080",
                                                        "container-123",
                                                    )
                                                ),
                                            ):
                                                import time

                                                enqueued_at = (
                                                    time.perf_counter() - 0.1
                                                )  # 100ms ago

                                                await TaskDispatcher.dispatch(
                                                    task_id="task-123",
                                                    session_id="session-456",
                                                    prompt="Hello",
                                                    config={"user_id": "user-789"},
                                                    enqueued_at=enqueued_at,
                                                )

                                                mock_executor_client.execute_task.assert_called_once()

    async def test_dispatch_subagent_stager_exception(self) -> None:
        """Test dispatch handles subagent stager exception gracefully."""
        with patch("app.scheduler.task_dispatcher.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.callback_base_url = "http://callback"
            mock_settings_obj.callback_token = "token"
            mock_settings.return_value = mock_settings_obj

            mock_executor_client = MagicMock()
            mock_executor_client.execute_task = AsyncMock()

            mock_backend_client = MagicMock()
            mock_backend_client.resolve_slash_commands = AsyncMock(return_value={})
            mock_backend_client.update_session_status = AsyncMock()

            mock_config_resolver = MagicMock()
            mock_config_resolver.resolve = AsyncMock(
                return_value={
                    "subagent_raw_agents": {"agent1": {"spec": {}}},
                }
            )

            mock_skill_stager = MagicMock()
            mock_skill_stager.stage_skills = MagicMock(return_value={})

            mock_plugin_stager = MagicMock()
            mock_plugin_stager.stage_plugins = MagicMock(return_value={})

            mock_attachment_stager = MagicMock()
            mock_attachment_stager.stage_inputs = MagicMock(return_value=[])

            mock_slash_command_stager = MagicMock()
            mock_slash_command_stager.stage_commands = MagicMock(return_value={})

            mock_subagent_stager = MagicMock()
            mock_subagent_stager.stage_raw_agents = MagicMock(
                side_effect=ValueError("Invalid agent")
            )

            with patch(
                "app.scheduler.task_dispatcher.ExecutorClient",
                return_value=mock_executor_client,
            ):
                with patch(
                    "app.scheduler.task_dispatcher.BackendClient",
                    return_value=mock_backend_client,
                ):
                    with patch(
                        "app.scheduler.task_dispatcher.ConfigResolver",
                        return_value=mock_config_resolver,
                    ):
                        with patch(
                            "app.scheduler.task_dispatcher.SkillStager",
                            return_value=mock_skill_stager,
                        ):
                            with patch(
                                "app.scheduler.task_dispatcher.PluginStager",
                                return_value=mock_plugin_stager,
                            ):
                                with patch(
                                    "app.scheduler.task_dispatcher.AttachmentStager",
                                    return_value=mock_attachment_stager,
                                ):
                                    with patch(
                                        "app.scheduler.task_dispatcher.SlashCommandStager",
                                        return_value=mock_slash_command_stager,
                                    ):
                                        with patch(
                                            "app.scheduler.task_dispatcher.SubAgentStager",
                                            return_value=mock_subagent_stager,
                                        ):
                                            with patch.object(
                                                TaskDispatcher,
                                                "resolve_executor_target",
                                                AsyncMock(
                                                    return_value=(
                                                        "http://executor:8080",
                                                        "container-123",
                                                    )
                                                ),
                                            ):
                                                # Should not raise - subagent exception is caught and logged
                                                await TaskDispatcher.dispatch(
                                                    task_id="task-123",
                                                    session_id="session-456",
                                                    prompt="Hello",
                                                    config={"user_id": "user-789"},
                                                )

                                                mock_executor_client.execute_task.assert_called_once()


if __name__ == "__main__":
    unittest.main()
