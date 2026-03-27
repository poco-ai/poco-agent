"""Tests for app/core/lifespan.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLifespan(unittest.TestCase):
    """Test lifespan context manager."""

    def test_lifespan_starts_scheduler(self) -> None:
        """Test that lifespan starts the scheduler."""
        with (
            patch("app.core.lifespan.get_settings") as mock_get_settings,
            patch("app.core.lifespan.scheduler") as mock_scheduler,
        ):
            mock_settings = MagicMock()
            mock_settings.task_pull_enabled = False
            mock_settings.workspace_cleanup_enabled = False
            mock_settings.scheduled_tasks_enabled = False
            mock_get_settings.return_value = mock_settings

            from app.core.lifespan import lifespan

            # Create a mock app
            mock_app = MagicMock()

            # Run the lifespan context manager
            import asyncio

            async def run_lifespan():
                async with lifespan(mock_app):
                    pass

            asyncio.run(run_lifespan())

            mock_scheduler.start.assert_called_once()
            mock_scheduler.shutdown.assert_called_once()

    def test_lifespan_with_task_pull_enabled(self) -> None:
        """Test lifespan with task pull enabled."""
        with (
            patch("app.core.lifespan.get_settings") as mock_get_settings,
            patch("app.core.lifespan.scheduler") as _mock_scheduler,
            patch(
                "app.services.run_pull_service.RunPullService"
            ) as mock_pull_service_cls,
            patch(
                "app.scheduler.pull_schedule_config.load_pull_schedule_config"
            ) as mock_load_config,
            patch(
                "app.scheduler.pull_schedule_config.default_pull_schedule_config_from_settings"
            ) as mock_default_config,
            patch(
                "app.scheduler.pull_job_registry.register_pull_jobs"
            ) as mock_register,
            patch(
                "app.scheduler.pull_job_registry.unregister_pull_jobs"
            ) as mock_unregister,
        ):
            mock_settings = MagicMock()
            mock_settings.task_pull_enabled = True
            mock_settings.workspace_cleanup_enabled = False
            mock_settings.scheduled_tasks_enabled = False
            mock_settings.schedule_config_path = None
            mock_get_settings.return_value = mock_settings

            mock_pull_service = MagicMock()
            mock_pull_service.shutdown = AsyncMock()
            mock_pull_service_cls.return_value = mock_pull_service

            mock_load_config.return_value = None
            mock_default_config.return_value = {"queues": []}
            mock_register.return_value = ["job-1"]

            from app.core.lifespan import lifespan

            mock_app = MagicMock()

            import asyncio

            async def run_lifespan():
                async with lifespan(mock_app):
                    pass

            asyncio.run(run_lifespan())

            mock_pull_service_cls.assert_called_once()
            mock_register.assert_called_once()
            mock_pull_service.shutdown.assert_called_once()
            mock_unregister.assert_called_once()

    def test_lifespan_with_workspace_cleanup_enabled(self) -> None:
        """Test lifespan with workspace cleanup enabled."""
        with (
            patch("app.core.lifespan.get_settings") as mock_get_settings,
            patch("app.core.lifespan.scheduler") as mock_scheduler,
            patch("app.services.cleanup_service.CleanupService") as mock_cleanup_cls,
        ):
            mock_settings = MagicMock()
            mock_settings.task_pull_enabled = False
            mock_settings.workspace_cleanup_enabled = True
            mock_settings.scheduled_tasks_enabled = False
            mock_get_settings.return_value = mock_settings

            from app.core.lifespan import lifespan

            mock_app = MagicMock()

            import asyncio

            async def run_lifespan():
                async with lifespan(mock_app):
                    pass

            asyncio.run(run_lifespan())

            mock_cleanup_cls.assert_called_once_with(mock_scheduler)

    def test_lifespan_with_scheduled_tasks_enabled(self) -> None:
        """Test lifespan with scheduled tasks enabled."""
        with (
            patch("app.core.lifespan.get_settings") as mock_get_settings,
            patch("app.core.lifespan.scheduler") as mock_scheduler,
            patch(
                "app.services.scheduled_task_dispatch_service.ScheduledTaskDispatchService"
            ) as mock_dispatch_cls,
        ):
            mock_settings = MagicMock()
            mock_settings.task_pull_enabled = False
            mock_settings.workspace_cleanup_enabled = False
            mock_settings.scheduled_tasks_enabled = True
            mock_settings.scheduled_tasks_dispatch_interval_seconds = 30
            mock_get_settings.return_value = mock_settings

            mock_dispatch_service = MagicMock()
            mock_dispatch_service.dispatch_due = AsyncMock()
            mock_dispatch_cls.return_value = mock_dispatch_service

            from app.core.lifespan import lifespan

            mock_app = MagicMock()

            import asyncio

            async def run_lifespan():
                async with lifespan(mock_app):
                    pass

            asyncio.run(run_lifespan())

            mock_dispatch_cls.assert_called_once()
            mock_scheduler.add_job.assert_called_once()
            call_kwargs = mock_scheduler.add_job.call_args[1]
            assert call_kwargs["trigger"] == "interval"
            assert call_kwargs["seconds"] == 30
            assert call_kwargs["id"] == "dispatch-scheduled-tasks"

    def test_lifespan_scheduled_tasks_min_interval(self) -> None:
        """Test that scheduled tasks interval is clamped to min 5 seconds."""
        with (
            patch("app.core.lifespan.get_settings") as mock_get_settings,
            patch("app.core.lifespan.scheduler") as mock_scheduler,
            patch(
                "app.services.scheduled_task_dispatch_service.ScheduledTaskDispatchService"
            ) as mock_dispatch_cls,
        ):
            mock_settings = MagicMock()
            mock_settings.task_pull_enabled = False
            mock_settings.workspace_cleanup_enabled = False
            mock_settings.scheduled_tasks_enabled = True
            mock_settings.scheduled_tasks_dispatch_interval_seconds = 2  # Below min
            mock_get_settings.return_value = mock_settings

            mock_dispatch_service = MagicMock()
            mock_dispatch_service.dispatch_due = AsyncMock()
            mock_dispatch_cls.return_value = mock_dispatch_service

            from app.core.lifespan import lifespan

            mock_app = MagicMock()

            import asyncio

            async def run_lifespan():
                async with lifespan(mock_app):
                    pass

            asyncio.run(run_lifespan())

            call_kwargs = mock_scheduler.add_job.call_args[1]
            # Should be clamped to min 5
            assert call_kwargs["seconds"] == 5


if __name__ == "__main__":
    unittest.main()
