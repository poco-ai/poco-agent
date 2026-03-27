import unittest
from unittest.mock import MagicMock, patch

from app.services.cleanup_service import CleanupService


class TestCleanupServiceInit(unittest.TestCase):
    """Test CleanupService.__init__."""

    def test_init_schedules_cleanup_job(self) -> None:
        """Test that init schedules the cleanup job."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            CleanupService(scheduler=mock_scheduler)

            mock_scheduler.add_job.assert_called_once()
            call_kwargs = mock_scheduler.add_job.call_args[1]
            assert call_kwargs["trigger"] == "cron"
            assert call_kwargs["hour"] == 2
            assert call_kwargs["minute"] == 0
            assert call_kwargs["id"] == "cleanup-workspaces"
            assert call_kwargs["replace_existing"] is True

    def test_init_creates_workspace_manager(self) -> None:
        """Test that init creates a WorkspaceManager instance."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace = MagicMock()
            mock_workspace_cls.return_value = mock_workspace

            service = CleanupService(scheduler=mock_scheduler)

            mock_workspace_cls.assert_called_once()
            assert service.workspace_manager is mock_workspace


class TestCleanupServiceCleanupExpiredWorkspaces(unittest.TestCase):
    """Test CleanupService.cleanup_expired_workspaces."""

    def test_cleanup_success(self) -> None:
        """Test successful cleanup."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace = MagicMock()
            mock_workspace.cleanup_expired_workspaces.return_value = {
                "cleaned": 5,
                "archived": 2,
                "errors": 0,
            }
            mock_workspace.get_disk_usage.return_value = {
                "usage_percent": 45.5,
                "used_gb": 100.0,
                "total_gb": 220.0,
            }
            mock_workspace_cls.return_value = mock_workspace

            service = CleanupService(scheduler=mock_scheduler)

            # Run the async method
            import asyncio

            asyncio.run(service.cleanup_expired_workspaces())

            mock_workspace.cleanup_expired_workspaces.assert_called_once()
            mock_workspace.get_disk_usage.assert_called_once()

    def test_cleanup_with_zero_cleaned(self) -> None:
        """Test cleanup when nothing is cleaned."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace = MagicMock()
            mock_workspace.cleanup_expired_workspaces.return_value = {
                "cleaned": 0,
                "archived": 0,
                "errors": 0,
            }
            mock_workspace.get_disk_usage.return_value = {
                "usage_percent": 10.0,
                "used_gb": 20.0,
                "total_gb": 200.0,
            }
            mock_workspace_cls.return_value = mock_workspace

            service = CleanupService(scheduler=mock_scheduler)

            import asyncio

            asyncio.run(service.cleanup_expired_workspaces())

            mock_workspace.cleanup_expired_workspaces.assert_called_once()

    def test_cleanup_handles_exception(self) -> None:
        """Test that cleanup handles exceptions gracefully."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace = MagicMock()
            mock_workspace.cleanup_expired_workspaces.side_effect = Exception(
                "DB connection failed"
            )
            mock_workspace_cls.return_value = mock_workspace

            service = CleanupService(scheduler=mock_scheduler)

            # Should not raise, just log error
            import asyncio

            asyncio.run(service.cleanup_expired_workspaces())

            mock_workspace.cleanup_expired_workspaces.assert_called_once()
            # get_disk_usage should not be called after exception
            mock_workspace.get_disk_usage.assert_not_called()

    def test_cleanup_handles_get_disk_usage_exception(self) -> None:
        """Test that cleanup handles get_disk_usage exceptions."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace = MagicMock()
            mock_workspace.cleanup_expired_workspaces.return_value = {
                "cleaned": 1,
                "archived": 0,
                "errors": 0,
            }
            mock_workspace.get_disk_usage.side_effect = Exception("Disk error")
            mock_workspace_cls.return_value = mock_workspace

            service = CleanupService(scheduler=mock_scheduler)

            # Should not raise
            import asyncio

            asyncio.run(service.cleanup_expired_workspaces())

            mock_workspace.cleanup_expired_workspaces.assert_called_once()
            mock_workspace.get_disk_usage.assert_called_once()


class TestCleanupServiceScheduleCleanupJob(unittest.TestCase):
    """Test CleanupService._schedule_cleanup_job."""

    def test_schedule_cleanup_job_called_on_init(self) -> None:
        """Test that _schedule_cleanup_job is called during init."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            CleanupService(scheduler=mock_scheduler)

            # Verify the job was added with correct parameters
            assert mock_scheduler.add_job.call_count == 1

    def test_schedule_cleanup_job_replaces_existing(self) -> None:
        """Test that replace_existing is True."""
        mock_scheduler = MagicMock()

        with patch(
            "app.services.cleanup_service.WorkspaceManager"
        ) as mock_workspace_cls:
            mock_workspace_cls.return_value = MagicMock()

            CleanupService(scheduler=mock_scheduler)

            call_kwargs = mock_scheduler.add_job.call_args[1]
            assert call_kwargs["replace_existing"] is True


if __name__ == "__main__":
    unittest.main()
