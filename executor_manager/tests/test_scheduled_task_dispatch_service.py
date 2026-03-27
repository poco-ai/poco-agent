import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scheduled_task_dispatch_service import (
    ScheduledTaskDispatchService,
)


class TestScheduledTaskDispatchServiceInit(unittest.TestCase):
    """Test ScheduledTaskDispatchService.__init__."""

    def test_init_with_defaults(self) -> None:
        """Test init creates BackendClient by default."""
        with (
            patch(
                "app.services.scheduled_task_dispatch_service.BackendClient"
            ) as mock_backend_cls,
            patch(
                "app.services.scheduled_task_dispatch_service.get_settings"
            ) as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.scheduled_tasks_dispatch_batch_size = 50
            mock_get_settings.return_value = mock_settings
            mock_backend_cls.return_value = MagicMock()

            service = ScheduledTaskDispatchService()

            mock_backend_cls.assert_called_once()
            assert service.settings is mock_settings

    def test_init_with_dependencies(self) -> None:
        """Test init with injected dependencies."""
        mock_backend = MagicMock()
        mock_settings = MagicMock()

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            assert service.backend_client is mock_backend
            assert service.settings is mock_settings


class TestScheduledTaskDispatchServiceDispatchDue(unittest.TestCase):
    """Test ScheduledTaskDispatchService.dispatch_due."""

    def _create_service(self, batch_size: int = 50) -> ScheduledTaskDispatchService:
        """Create service with mocked dependencies."""
        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            return_value={"dispatched": 5}
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = batch_size

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)
            return service

    def test_dispatch_due_success(self) -> None:
        """Test successful dispatch."""
        service = self._create_service()

        import asyncio

        asyncio.run(service.dispatch_due())

        service.backend_client.dispatch_due_scheduled_tasks.assert_called_once()
        call_kwargs = service.backend_client.dispatch_due_scheduled_tasks.call_args[1]
        assert call_kwargs["limit"] == 50

    def test_dispatch_due_with_custom_batch_size(self) -> None:
        """Test dispatch with custom batch size."""
        service = self._create_service(batch_size=100)

        import asyncio

        asyncio.run(service.dispatch_due())

        call_kwargs = service.backend_client.dispatch_due_scheduled_tasks.call_args[1]
        assert call_kwargs["limit"] == 100

    def test_dispatch_due_with_zero_batch_size(self) -> None:
        """Test dispatch with zero batch size (should use min 1)."""
        service = self._create_service(batch_size=0)

        import asyncio

        asyncio.run(service.dispatch_due())

        call_kwargs = service.backend_client.dispatch_due_scheduled_tasks.call_args[1]
        # max(1, int(0)) = 1
        assert call_kwargs["limit"] == 1

    def test_dispatch_due_with_negative_batch_size(self) -> None:
        """Test dispatch with negative batch size (should use min 1)."""
        service = self._create_service(batch_size=-10)

        import asyncio

        asyncio.run(service.dispatch_due())

        call_kwargs = service.backend_client.dispatch_due_scheduled_tasks.call_args[1]
        # max(1, int(-10)) = 1
        assert call_kwargs["limit"] == 1

    def test_dispatch_due_returns_payload(self) -> None:
        """Test dispatch returns expected payload."""
        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            return_value={"dispatched": 10, "errors": 0}
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = 50

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            import asyncio

            asyncio.run(service.dispatch_due())

            # Verify the call was made (logging is verified indirectly)
            assert service.backend_client.dispatch_due_scheduled_tasks.called

    def test_dispatch_due_handles_exception(self) -> None:
        """Test dispatch handles exceptions gracefully."""
        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            side_effect=Exception("Backend error")
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = 50

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            import asyncio

            # Should not raise, just log error
            asyncio.run(service.dispatch_due())

            assert service.backend_client.dispatch_due_scheduled_tasks.called

    def test_dispatch_due_handles_timeout_error(self) -> None:
        """Test dispatch handles timeout errors."""
        import asyncio

        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timed out")
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = 50

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            # Should not raise, just log error
            asyncio.run(service.dispatch_due())

    def test_dispatch_due_handles_connection_error(self) -> None:
        """Test dispatch handles connection errors."""
        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            side_effect=ConnectionError("Failed to connect")
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = 50

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            import asyncio

            # Should not raise, just log error
            asyncio.run(service.dispatch_due())

    def test_dispatch_due_with_float_batch_size(self) -> None:
        """Test dispatch with float batch size (should convert to int)."""
        mock_backend = MagicMock()
        mock_backend.dispatch_due_scheduled_tasks = AsyncMock(
            return_value={"dispatched": 5}
        )

        mock_settings = MagicMock()
        mock_settings.scheduled_tasks_dispatch_batch_size = 25.7  # Float value

        with patch(
            "app.services.scheduled_task_dispatch_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            service = ScheduledTaskDispatchService(backend_client=mock_backend)

            import asyncio

            asyncio.run(service.dispatch_due())

            call_kwargs = service.backend_client.dispatch_due_scheduled_tasks.call_args[
                1
            ]
            # int(25.7) = 25
            assert call_kwargs["limit"] == 25


if __name__ == "__main__":
    unittest.main()
