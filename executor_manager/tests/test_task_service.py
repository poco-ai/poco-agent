import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.task import (
    SessionStatusResponse,
    TaskCreateResponse,
    TaskStatusResponse,
)
from app.services.task_service import TaskService


class TestTaskServiceInit(unittest.TestCase):
    """Test TaskService.__init__."""

    def test_init(self) -> None:
        """Test init creates settings."""
        mock_settings = MagicMock()

        with patch(
            "app.services.task_service.get_settings", return_value=mock_settings
        ):
            service = TaskService()

            assert service.settings is mock_settings


class TestTaskServiceCreateTask(unittest.TestCase):
    """Test TaskService.create_task."""

    def _create_service(self) -> TaskService:
        """Create TaskService with mocked settings."""
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"

        with patch(
            "app.services.task_service.get_settings", return_value=mock_settings
        ):
            return TaskService()

    def test_create_task_new_session(self) -> None:
        """Test creating a task with a new backend run."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            return_value={
                "session_id": "new-session-123",
                "accepted_type": "run",
                "run_id": "run-123",
                "status": "queued",
            }
        )

        with (
            patch(
                "app.services.backend_client.BackendClient",
                return_value=mock_backend_client,
            ),
        ):
            import asyncio

            result = asyncio.run(
                service.create_task(
                    user_id="user-123",
                    prompt="Test prompt",
                    config={"browser_enabled": False},
                    session_id=None,
                )
            )

            assert isinstance(result, TaskCreateResponse)
            assert result.session_id == "new-session-123"
            assert result.task_id == "run-123"
            assert result.status == "queued"
            assert result.task_type == "run"
            mock_backend_client.enqueue_task_from_manager.assert_called_once()

    def test_create_task_continue_session(self) -> None:
        """Test creating a task with an existing session."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            return_value={
                "session_id": "existing-session",
                "accepted_type": "queued_query",
                "queue_item_id": "queue-123",
                "status": "queued",
            }
        )

        with (
            patch(
                "app.services.backend_client.BackendClient",
                return_value=mock_backend_client,
            ),
        ):
            import asyncio

            result = asyncio.run(
                service.create_task(
                    user_id="user-123",
                    prompt="Continue prompt",
                    config={"browser_enabled": False},
                    session_id="existing-session",
                )
            )

            assert result.session_id == "existing-session"
            assert result.task_id == "queue-123"
            assert result.task_type == "queued_query"
            mock_backend_client.enqueue_task_from_manager.assert_called_once()

    def test_create_task_with_persistent_container(self) -> None:
        """Test creating a task with persistent container mode."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            return_value={
                "session_id": "session-123",
                "accepted_type": "run",
                "run_id": "run-123",
                "status": "queued",
            }
        )

        with (
            patch(
                "app.services.backend_client.BackendClient",
                return_value=mock_backend_client,
            ),
            patch(
                "app.scheduler.task_dispatcher.TaskDispatcher.resolve_executor_target",
                new_callable=AsyncMock,
                return_value=("container-123", "container-123"),
            ),
        ):
            import asyncio

            result = asyncio.run(
                service.create_task(
                    user_id="user-123",
                    prompt="Test prompt",
                    config={"container_mode": "persistent", "browser_enabled": False},
                    session_id=None,
                )
            )

            assert result.container_id == "container-123"

    def test_create_task_with_container_id(self) -> None:
        """Test creating a task with a specific container ID."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            return_value={
                "session_id": "session-123",
                "accepted_type": "run",
                "run_id": "run-123",
                "status": "queued",
            }
        )

        with (
            patch(
                "app.services.backend_client.BackendClient",
                return_value=mock_backend_client,
            ),
            patch(
                "app.scheduler.task_dispatcher.TaskDispatcher.resolve_executor_target",
                new_callable=AsyncMock,
                return_value=("existing-container", "existing-container"),
            ),
        ):
            import asyncio

            result = asyncio.run(
                service.create_task(
                    user_id="user-123",
                    prompt="Test prompt",
                    config={
                        "container_id": "existing-container",
                        "container_mode": "ephemeral",
                        "browser_enabled": False,
                    },
                    session_id=None,
                )
            )

            assert result.container_id == "existing-container"

    def test_create_task_http_error(self) -> None:
        """Test create_task handles HTTP errors."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Bad request"
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )
        )

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with self.assertRaises(AppException) as ctx:
                asyncio.run(
                    service.create_task(
                        user_id="user-123",
                        prompt="Test prompt",
                        config={"browser_enabled": False},
                        session_id=None,
                    )
                )

            assert ctx.exception.error_code == ErrorCode.TASK_SCHEDULING_FAILED

    def test_create_task_generic_error(self) -> None:
        """Test create_task handles generic errors."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.enqueue_task_from_manager = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with self.assertRaises(AppException) as ctx:
                asyncio.run(
                    service.create_task(
                        user_id="user-123",
                        prompt="Test prompt",
                        config={"browser_enabled": False},
                        session_id=None,
                    )
                )

            assert ctx.exception.error_code == ErrorCode.TASK_SCHEDULING_FAILED


class TestTaskServiceGetTaskStatus(unittest.TestCase):
    """Test TaskService.get_task_status."""

    def _create_service(self) -> TaskService:
        """Create TaskService with mocked settings."""
        mock_settings = MagicMock()

        with patch(
            "app.services.task_service.get_settings", return_value=mock_settings
        ):
            return TaskService()

    def test_get_task_status_found(self) -> None:
        """Test getting status of an existing backend task."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.get_internal_task_status = AsyncMock(
            return_value={
                "task_id": "task-123",
                "task_type": "run",
                "session_id": "session-123",
                "status": "running",
            }
        )

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            result = asyncio.run(service.get_task_status("task-123"))

            assert isinstance(result, TaskStatusResponse)
            assert result.task_id == "task-123"
            assert result.status == "running"
            assert result.task_type == "run"
            assert result.session_id == "session-123"
            assert result.next_run_time is None

    def test_get_task_status_not_found(self) -> None:
        """Test getting status of a non-existent task."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_backend_client = MagicMock()
        mock_backend_client.get_internal_task_status = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            )
        )

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with self.assertRaises(AppException) as ctx:
                asyncio.run(service.get_task_status("nonexistent-task"))

            assert ctx.exception.error_code == ErrorCode.TASK_NOT_FOUND
            assert "Task not found" in ctx.exception.message

    def test_get_task_status_backend_unavailable(self) -> None:
        """Test backend failures propagate as backend unavailable."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_backend_client = MagicMock()
        mock_backend_client.get_internal_task_status = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with self.assertRaises(AppException) as ctx:
                asyncio.run(service.get_task_status("task-123"))

            assert ctx.exception.error_code == ErrorCode.BACKEND_UNAVAILABLE


class TestTaskServiceGetSessionStatus(unittest.TestCase):
    """Test TaskService.get_session_status."""

    def _create_service(self) -> TaskService:
        """Create TaskService with mocked settings."""
        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = "test-key"

        with patch(
            "app.services.task_service.get_settings", return_value=mock_settings
        ):
            return TaskService()

    def test_get_session_status_success(self) -> None:
        """Test getting session status successfully."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "data": {
                    "session_id": "session-123",
                    "user_id": "user-123",
                    "sdk_session_id": "sdk-123",
                    "status": "running",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T01:00:00Z",
                }
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_backend_client = MagicMock()
        mock_backend_client.settings = MagicMock()
        mock_backend_client.settings.backend_url = "http://localhost:8000"
        mock_backend_client._trace_headers = MagicMock(return_value={})

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            # Create a mock async context manager
            async def mock_async_client():
                mock_client = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                return mock_client

            with patch(
                "app.services.task_service.httpx.AsyncClient"
            ) as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = asyncio.run(service.get_session_status("session-123"))

                assert isinstance(result, SessionStatusResponse)
                assert result.session_id == "session-123"
                assert result.user_id == "user-123"

    def test_get_session_status_not_found(self) -> None:
        """Test getting non-existent session status."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            )
        )

        mock_backend_client = MagicMock()
        mock_backend_client.settings = MagicMock()
        mock_backend_client.settings.backend_url = "http://localhost:8000"
        mock_backend_client._trace_headers = MagicMock(return_value={})

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with patch(
                "app.services.task_service.httpx.AsyncClient"
            ) as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                with self.assertRaises(AppException) as ctx:
                    asyncio.run(service.get_session_status("nonexistent-session"))

                assert ctx.exception.error_code == ErrorCode.SESSION_NOT_FOUND

    def test_get_session_status_backend_unavailable(self) -> None:
        """Test handling backend unavailable error."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )

        mock_backend_client = MagicMock()
        mock_backend_client.settings = MagicMock()
        mock_backend_client.settings.backend_url = "http://localhost:8000"
        mock_backend_client._trace_headers = MagicMock(return_value={})

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with patch(
                "app.services.task_service.httpx.AsyncClient"
            ) as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                with self.assertRaises(AppException) as ctx:
                    asyncio.run(service.get_session_status("session-123"))

                assert ctx.exception.error_code == ErrorCode.BACKEND_UNAVAILABLE

    def test_get_session_status_generic_error(self) -> None:
        """Test handling generic errors."""
        service = self._create_service()

        mock_backend_client = MagicMock()
        mock_backend_client.settings = MagicMock()
        mock_backend_client.settings.backend_url = "http://localhost:8000"
        mock_backend_client._trace_headers = MagicMock(return_value={})

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with patch(
                "app.services.task_service.httpx.AsyncClient"
            ) as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(side_effect=Exception("Network error"))
                mock_client_cls.return_value = mock_client

                with self.assertRaises(AppException) as ctx:
                    asyncio.run(service.get_session_status("session-123"))

                assert ctx.exception.error_code == ErrorCode.BACKEND_UNAVAILABLE

    def test_get_session_status_unwrapped_response(self) -> None:
        """Test handling response without 'data' wrapper."""
        service = self._create_service()

        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "session_id": "session-123",
                "user_id": "user-123",
                "status": "running",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T01:00:00Z",
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_backend_client = MagicMock()
        mock_backend_client.settings = MagicMock()
        mock_backend_client.settings.backend_url = "http://localhost:8000"
        mock_backend_client._trace_headers = MagicMock(return_value={})

        with patch(
            "app.services.backend_client.BackendClient",
            return_value=mock_backend_client,
        ):
            import asyncio

            with patch(
                "app.services.task_service.httpx.AsyncClient"
            ) as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = asyncio.run(service.get_session_status("session-123"))

                assert result.session_id == "session-123"


if __name__ == "__main__":
    unittest.main()
