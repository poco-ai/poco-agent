import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.task_dispatcher import TaskDispatcher


class TestTaskDispatcherGetContainerPool(unittest.TestCase):
    """Test TaskDispatcher.get_container_pool."""

    def tearDown(self) -> None:
        TaskDispatcher.container_pool = None

    def test_creates_pool_if_none(self) -> None:
        TaskDispatcher.container_pool = None

        with patch("app.scheduler.task_dispatcher.ContainerPool") as mock_pool_cls:
            mock_pool = MagicMock()
            mock_pool_cls.return_value = mock_pool

            result = TaskDispatcher.get_container_pool()

            assert result == mock_pool
            mock_pool_cls.assert_called_once()

    def test_returns_existing_pool(self) -> None:
        mock_pool = MagicMock()
        TaskDispatcher.container_pool = mock_pool

        result = TaskDispatcher.get_container_pool()

        assert result == mock_pool


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

        TaskDispatcher.container_pool = None
