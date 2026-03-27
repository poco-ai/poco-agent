"""Tests for run_pull_service.py."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.run_pull_service import (
    RunPullService,
    _extract_enabled_skill_names,
)


class TestExtractEnabledSkillNames(unittest.TestCase):
    """Test _extract_enabled_skill_names pure function."""

    def test_empty_dict(self) -> None:
        """Test with empty dict."""
        result = _extract_enabled_skill_names({})
        assert result == []

    def test_none_input(self) -> None:
        """Test with None input."""
        result = _extract_enabled_skill_names(None)
        assert result == []

    def test_list_input(self) -> None:
        """Test with list input (not dict)."""
        result = _extract_enabled_skill_names(["skill1", "skill2"])
        assert result == []

    def test_simple_skills(self) -> None:
        """Test with simple enabled skills."""
        result = _extract_enabled_skill_names(
            {
                "skill1": {},
                "skill2": {"enabled": True},
            }
        )
        assert result == ["skill1", "skill2"]

    def test_disabled_skill_excluded(self) -> None:
        """Test that disabled skills are excluded."""
        result = _extract_enabled_skill_names(
            {
                "skill1": {},
                "skill2": {"enabled": False},
            }
        )
        assert result == ["skill1"]

    def test_empty_name_skipped(self) -> None:
        """Test that empty names are skipped."""
        result = _extract_enabled_skill_names(
            {
                "skill1": {},
                "": {},
                "  ": {},
            }
        )
        assert result == ["skill1"]

    def test_non_string_name_skipped(self) -> None:
        """Test that non-string names are skipped."""
        result = _extract_enabled_skill_names(
            {
                "skill1": {},
                123: {},  # type: ignore
                None: {},  # type: ignore
            }
        )
        assert result == ["skill1"]

    def test_whitespace_trimmed(self) -> None:
        """Test that names are trimmed."""
        result = _extract_enabled_skill_names(
            {
                "  skill1  ": {},
                "skill2": {},
            }
        )
        assert "skill1" in result
        assert "skill2" in result

    def test_returns_sorted(self) -> None:
        """Test that result is sorted."""
        result = _extract_enabled_skill_names(
            {
                "zebra": {},
                "alpha": {},
                "beta": {},
            }
        )
        assert result == ["alpha", "beta", "zebra"]

    def test_deduplication(self) -> None:
        """Test that duplicate names are deduplicated."""
        result = _extract_enabled_skill_names(
            {
                "skill1": {},
                "  skill1  ": {},  # Same after trim
            }
        )
        assert result == ["skill1"]


class TestGetWindowLock(unittest.TestCase):
    """Test RunPullService._get_window_lock."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_creates_new_lock(self) -> None:
        """Test creating a new lock for a window."""
        service = self._create_service()
        lock = service._get_window_lock("window-1")

        assert isinstance(lock, asyncio.Lock)
        assert "window-1" in service._window_locks

    def test_returns_existing_lock(self) -> None:
        """Test returning existing lock."""
        service = self._create_service()
        lock1 = service._get_window_lock("window-1")
        lock2 = service._get_window_lock("window-1")

        assert lock1 is lock2

    def test_different_windows_different_locks(self) -> None:
        """Test different windows get different locks."""
        service = self._create_service()
        lock1 = service._get_window_lock("window-1")
        lock2 = service._get_window_lock("window-2")

        assert lock1 is not lock2


class TestSetWindowUntil(unittest.TestCase):
    """Test RunPullService.set_window_until."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_sets_window_until(self) -> None:
        """Test setting window until time."""
        service = self._create_service()
        until = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        service.set_window_until("window-1", until)

        assert service._windows_until["window-1"] == until

    def test_empty_window_id_ignored(self) -> None:
        """Test empty window_id is ignored."""
        service = self._create_service()
        until = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        service.set_window_until("", until)
        service.set_window_until("   ", until)

        assert service._windows_until == {}

    def test_naive_datetime_gets_utc(self) -> None:
        """Test naive datetime gets UTC timezone."""
        service = self._create_service()
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)  # No timezone

        service.set_window_until("window-1", naive_dt)

        result = service._windows_until["window-1"]
        assert result.tzinfo == timezone.utc


class TestRegisterInflightRun(unittest.TestCase):
    """Test RunPullService._register_inflight_run."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_registers_new_run(self) -> None:
        """Test registering a new run."""
        service = self._create_service()

        result = asyncio.run(service._register_inflight_run("run-1"))

        assert result is True
        assert "run-1" in service._inflight_run_ids

    def test_duplicate_run_returns_false(self) -> None:
        """Test duplicate run returns False."""
        service = self._create_service()

        asyncio.run(service._register_inflight_run("run-1"))
        result = asyncio.run(service._register_inflight_run("run-1"))

        assert result is False


class TestReleaseInflightRun(unittest.TestCase):
    """Test RunPullService._release_inflight_run."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_releases_run(self) -> None:
        """Test releasing a run."""
        service = self._create_service()
        asyncio.run(service._register_inflight_run("run-1"))

        asyncio.run(service._release_inflight_run("run-1"))

        assert "run-1" not in service._inflight_run_ids

    def test_release_nonexistent_run_safe(self) -> None:
        """Test releasing nonexistent run is safe."""
        service = self._create_service()

        # Should not raise
        asyncio.run(service._release_inflight_run("nonexistent"))


class TestOpenWindow(unittest.TestCase):
    """Test RunPullService.open_window."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            service = RunPullService()
            service.poll = AsyncMock()  # Mock poll to avoid backend calls
            return service

    def test_open_window_when_shutdown(self) -> None:
        """Test open_window returns early when shutdown."""
        service = self._create_service()
        service._shutdown = True

        asyncio.run(service.open_window("window-1"))

        assert service.poll.called is False

    def test_open_window_empty_id(self) -> None:
        """Test open_window with empty window_id."""
        service = self._create_service()

        asyncio.run(service.open_window(""))

        assert service.poll.called is False

    def test_open_window_sets_until_time(self) -> None:
        """Test open_window sets until time."""
        service = self._create_service()

        asyncio.run(service.open_window("window-1", window_minutes=30))

        assert "window-1" in service._windows_until
        assert service.poll.called is True

    def test_open_window_negative_minutes_defaults(self) -> None:
        """Test open_window with negative minutes defaults to 60."""
        service = self._create_service()

        asyncio.run(service.open_window("window-1", window_minutes=-10))

        assert "window-1" in service._windows_until
        assert service.poll.called is True


class TestPollWindow(unittest.TestCase):
    """Test RunPullService.poll_window."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            service = RunPullService()
            service.poll = AsyncMock()
            return service

    def test_poll_window_when_shutdown(self) -> None:
        """Test poll_window returns early when shutdown."""
        service = self._create_service()
        service._shutdown = True

        asyncio.run(service.poll_window("window-1"))

        assert service.poll.called is False

    def test_poll_window_empty_id(self) -> None:
        """Test poll_window with empty window_id."""
        service = self._create_service()

        asyncio.run(service.poll_window(""))

        assert service.poll.called is False

    def test_poll_window_no_until_set(self) -> None:
        """Test poll_window when no until time set."""
        service = self._create_service()

        asyncio.run(service.poll_window("window-1"))

        assert service.poll.called is False

    def test_poll_window_expired(self) -> None:
        """Test poll_window when window has expired."""
        service = self._create_service()
        service._windows_until["window-1"] = datetime(
            2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )

        asyncio.run(service.poll_window("window-1"))

        assert service.poll.called is False
        assert "window-1" not in service._windows_until

    def test_poll_window_active(self) -> None:
        """Test poll_window with active window."""
        service = self._create_service()
        service._windows_until["window-1"] = datetime.now(timezone.utc) + timedelta(
            hours=1
        )

        asyncio.run(service.poll_window("window-1"))

        assert service.poll.called is True


class TestShutdown(unittest.TestCase):
    """Test RunPullService.shutdown."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_shutdown_sets_flag(self) -> None:
        """Test shutdown sets shutdown flag."""
        service = self._create_service()

        asyncio.run(service.shutdown())

        assert service._shutdown is True

    def test_shutdown_clears_tasks(self) -> None:
        """Test shutdown clears tasks."""
        service = self._create_service()

        asyncio.run(service.shutdown())

        assert service._tasks == set()


class TestPoll(unittest.TestCase):
    """Test RunPullService.poll."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient") as mock_backend,
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            mock_backend.return_value.claim_run = AsyncMock()
            return RunPullService()

    def test_poll_when_shutdown(self) -> None:
        """Test poll returns early when shutdown."""
        service = self._create_service()
        service._shutdown = True

        asyncio.run(service.poll())

        assert service.backend_client.claim_run.called is False

    def test_poll_no_claim(self) -> None:
        """Test poll when no run to claim."""
        service = self._create_service()
        service.backend_client.claim_run = AsyncMock(return_value=None)

        asyncio.run(service.poll())

        service.backend_client.claim_run.assert_called_once()

    def test_poll_claim_exception(self) -> None:
        """Test poll handles claim exception."""
        service = self._create_service()
        service.backend_client.claim_run = AsyncMock(
            side_effect=Exception("Backend error")
        )

        asyncio.run(service.poll())

        # Should not raise, just log error
        service.backend_client.claim_run.assert_called_once()


class TestOnTaskDone(unittest.TestCase):
    """Test RunPullService._on_task_done."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_on_task_done_removes_task(self) -> None:
        """Test _on_task_done removes task from set."""

        async def run_test() -> None:
            service = self._create_service()

            async def dummy_task() -> None:
                pass

            task = asyncio.create_task(dummy_task())
            service._tasks.add(task)

            await task  # Complete the task
            service._on_task_done(task)

            assert task not in service._tasks

        asyncio.run(run_test())

    def test_on_task_done_releases_semaphore(self) -> None:
        """Test _on_task_done releases semaphore."""

        async def run_test() -> None:
            service = self._create_service()

            async def dummy_task() -> None:
                pass

            task = asyncio.create_task(dummy_task())
            await service._semaphore.acquire()  # Lock semaphore

            await task
            service._on_task_done(task)

            # Semaphore should be released
            assert not service._semaphore.locked()

        asyncio.run(run_test())


class TestDrainTasks(unittest.TestCase):
    """Test RunPullService._drain_tasks."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_drain_tasks_empty(self) -> None:
        """Test _drain_tasks with no tasks."""
        service = self._create_service()

        asyncio.run(service._drain_tasks())

        assert service._tasks == set()

    def test_drain_tasks_cancels_tasks(self) -> None:
        """Test _drain_tasks cancels and clears tasks."""

        async def run_test() -> None:
            service = self._create_service()

            async def long_task() -> None:
                await asyncio.sleep(10)

            task1 = asyncio.create_task(long_task())
            task2 = asyncio.create_task(long_task())
            service._tasks.add(task1)
            service._tasks.add(task2)

            await service._drain_tasks()

            assert service._tasks == set()
            assert task1.cancelled()
            assert task2.cancelled()

        asyncio.run(run_test())


class TestPollWithClaim(unittest.TestCase):
    """Test RunPullService.poll with successful claim."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient") as mock_backend,
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            # Return a valid claim
            mock_backend.return_value.claim_run = AsyncMock(
                return_value={
                    "run": {"run_id": "run-1", "session_id": "sess-1"},
                    "user_id": "user-1",
                    "prompt": "test prompt",
                    "config_snapshot": {},
                }
            )
            return RunPullService()

    def test_poll_creates_task_on_claim(self) -> None:
        """Test poll creates task when claim succeeds."""
        service = self._create_service()

        # Run poll but cancel after task is created
        async def run_poll() -> None:
            task = asyncio.create_task(service.poll())
            # Wait for claim to be processed
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_poll())

        # Verify claim was called
        service.backend_client.claim_run.assert_called()


class TestHandleClaimDuplicateRun(unittest.TestCase):
    """Test RunPullService._handle_claim duplicate run detection."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_duplicate_run_skipped(self) -> None:
        """Test that duplicate run is skipped."""
        service = self._create_service()
        claim = {
            "run": {"run_id": "run-1", "session_id": "sess-1"},
            "user_id": "user-1",
            "prompt": "test",
            "config_snapshot": {},
        }

        # Register run first
        asyncio.run(service._register_inflight_run("run-1"))

        # Handle claim should skip duplicate
        asyncio.run(service._handle_claim(claim))

        # Should still only have one entry
        assert "run-1" in service._inflight_run_ids


class TestHandleClaimValidation(unittest.TestCase):
    """Test RunPullService._handle_claim validation logic."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_invalid_claim_missing_run_id(self) -> None:
        """Test claim with missing run_id returns early."""
        service = self._create_service()
        claim = {
            "run": {"session_id": "sess-1"},
            "user_id": "user-1",
            "prompt": "test",
        }

        asyncio.run(service._handle_claim(claim))

        assert service._inflight_run_ids == set()

    def test_invalid_claim_missing_session_id(self) -> None:
        """Test claim with missing session_id returns early."""
        service = self._create_service()
        claim = {
            "run": {"run_id": "run-1"},
            "user_id": "user-1",
            "prompt": "test",
        }

        asyncio.run(service._handle_claim(claim))

        assert service._inflight_run_ids == set()

    def test_invalid_claim_missing_user_id(self) -> None:
        """Test claim with missing user_id returns early."""
        service = self._create_service()
        claim = {
            "run": {"run_id": "run-1", "session_id": "sess-1"},
            "prompt": "test",
        }

        asyncio.run(service._handle_claim(claim))

        assert service._inflight_run_ids == set()

    def test_invalid_claim_missing_prompt(self) -> None:
        """Test claim with missing prompt returns early."""
        service = self._create_service()
        claim = {
            "run": {"run_id": "run-1", "session_id": "sess-1"},
            "user_id": "user-1",
        }

        asyncio.run(service._handle_claim(claim))

        assert service._inflight_run_ids == set()


class TestPollCancelledError(unittest.TestCase):
    """Test RunPullService.poll CancelledError handling (lines 178-179)."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=1,  # Set to 1 so semaphore locks after one acquire
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_poll_cancelled_error_releases_semaphore(self) -> None:
        """Test poll handles CancelledError and releases semaphore."""

        async def run_test() -> None:
            service = self._create_service()
            service.backend_client.claim_run = AsyncMock(
                side_effect=asyncio.CancelledError
            )

            # With max_concurrent_tasks=1, semaphore should be locked initially
            # poll() acquires semaphore first, then calls claim_run
            # If claim_run raises CancelledError, poll should release semaphore
            await service.poll()

            # Semaphore should be released after CancelledError
            # (poll acquires and releases on CancelledError)
            assert not service._semaphore.locked()

        asyncio.run(run_test())


class TestOnTaskDoneExceptionHandling(unittest.TestCase):
    """Test RunPullService._on_task_done exception handling (lines 207-208, 210)."""

    def _create_service(self) -> RunPullService:
        """Create service with mocked dependencies."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            return RunPullService()

    def test_on_task_done_with_exception(self) -> None:
        """Test _on_task_done logs when task has exception (line 210)."""

        async def run_test() -> None:
            service = self._create_service()

            async def failing_task() -> None:
                raise RuntimeError("Task failed")

            task = asyncio.create_task(failing_task())
            service._tasks.add(task)
            await service._semaphore.acquire()

            # Wait for task to complete
            try:
                await task
            except RuntimeError:
                pass

            # _on_task_done should handle the exception
            service._on_task_done(task)

            assert task not in service._tasks
            assert not service._semaphore.locked()

        asyncio.run(run_test())

    def test_on_task_done_cancelled_task(self) -> None:
        """Test _on_task_done handles CancelledError (lines 207-208)."""

        async def run_test() -> None:
            service = self._create_service()

            async def cancelled_task() -> None:
                await asyncio.sleep(10)

            task = asyncio.create_task(cancelled_task())
            service._tasks.add(task)
            await service._semaphore.acquire()

            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # _on_task_done should handle CancelledError from task.exception()
            service._on_task_done(task)

            assert task not in service._tasks

        asyncio.run(run_test())


class TestHandleClaimEmptyCallbackUrl(unittest.TestCase):
    """Test RunPullService._handle_claim with empty callback_base_url (line 255)."""

    def _create_service_with_empty_callback(self) -> RunPullService:
        """Create service with empty callback_base_url."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="",  # Empty callback URL
                callback_token="test-token",
            )
            return RunPullService()

    def test_handle_claim_empty_callback_url_raises(self) -> None:
        """Test _handle_claim raises ValueError when callback_base_url is empty."""

        async def run_test() -> None:
            service = self._create_service_with_empty_callback()
            claim = {
                "run": {"run_id": "run-1", "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            # Should raise ValueError for empty callback_base_url
            with self.assertRaises(ValueError) as ctx:
                await service._handle_claim(claim)

            assert "callback_base_url cannot be empty" in str(ctx.exception)
            # Run should be released from inflight set in finally block
            # (exception happens in try block, finally releases the run)

        asyncio.run(run_test())

    def test_handle_claim_none_callback_url_raises(self) -> None:
        """Test _handle_claim raises ValueError when callback_base_url is None."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient"),
            patch("app.services.run_pull_service.ExecutorClient"),
            patch("app.services.run_pull_service.ConfigResolver"),
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url=None,  # None callback URL
                callback_token="test-token",
            )
            service = RunPullService()

            async def run_test() -> None:
                claim = {
                    "run": {"run_id": "run-1", "session_id": "sess-1"},
                    "user_id": "user-1",
                    "prompt": "test",
                    "config_snapshot": {},
                }

                with self.assertRaises(ValueError) as ctx:
                    await service._handle_claim(claim)

                assert "callback_base_url cannot be empty" in str(ctx.exception)

            asyncio.run(run_test())


class TestHandleClaimMainFlow(unittest.TestCase):
    """Test RunPullService._handle_claim main flow (lines 263-485)."""

    def _create_service_with_all_deps(self) -> RunPullService:
        """Create service with all dependencies mocked."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient") as mock_backend_cls,
            patch("app.services.run_pull_service.ExecutorClient") as mock_executor_cls,
            patch("app.services.run_pull_service.ConfigResolver") as mock_resolver_cls,
            patch("app.services.run_pull_service.SkillStager") as mock_skill_cls,
            patch("app.services.run_pull_service.PluginStager") as mock_plugin_cls,
            patch("app.services.run_pull_service.AttachmentStager") as mock_attach_cls,
            patch("app.services.run_pull_service.ClaudeMdStager") as mock_claude_cls,
            patch("app.services.run_pull_service.SlashCommandStager") as mock_slash_cls,
            patch("app.services.run_pull_service.SubAgentStager") as mock_subagent_cls,
            patch(
                "app.services.run_pull_service.TaskDispatcher.get_container_pool"
            ) as mock_get_pool,
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )
            # Setup mock instances
            mock_backend = MagicMock()
            mock_backend.resolve_slash_commands = AsyncMock(return_value=[])
            mock_backend.get_claude_md = AsyncMock(return_value={})
            mock_backend.start_run = AsyncMock()
            mock_backend_cls.return_value = mock_backend

            mock_executor = MagicMock()
            mock_executor.execute_task = AsyncMock()
            mock_executor_cls.return_value = mock_executor

            mock_resolver = MagicMock()
            mock_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {},
                    "plugin_files": {},
                    "input_files": [],
                }
            )
            mock_resolver_cls.return_value = mock_resolver

            # Stagers return dict/list
            mock_skill = MagicMock()
            mock_skill.stage_skills = MagicMock(return_value={})
            mock_skill_cls.return_value = mock_skill

            mock_plugin = MagicMock()
            mock_plugin.stage_plugins = MagicMock(return_value={})
            mock_plugin_cls.return_value = mock_plugin

            mock_attach = MagicMock()
            mock_attach.stage_inputs = MagicMock(return_value=[])
            mock_attach_cls.return_value = mock_attach

            mock_claude = MagicMock()
            mock_claude.stage = MagicMock(return_value={})
            mock_claude_cls.return_value = mock_claude

            mock_slash = MagicMock()
            mock_slash.stage_commands = MagicMock(return_value=[])
            mock_slash_cls.return_value = mock_slash

            mock_subagent = MagicMock()
            mock_subagent.stage_raw_agents = MagicMock(return_value=[])
            mock_subagent_cls.return_value = mock_subagent

            # Mock container pool to prevent Docker initialization
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            mock_get_pool.return_value = mock_pool

            service = RunPullService()
            # Pre-set container_pool to avoid TaskDispatcher.get_container_pool() call
            service.container_pool = mock_pool
            return service

    def test_handle_claim_resolves_config(self) -> None:
        """Test ConfigResolver.resolve is called with correct params."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            claim = {
                "run": {"run_id": 123, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test prompt",
                "config_snapshot": {"key": "value"},
            }

            await service._handle_claim(claim)

            service.config_resolver.resolve.assert_called_once()
            # resolve uses positional args: (user_id, config_snapshot, session_id, run_id)
            call_args = service.config_resolver.resolve.call_args[0]
            assert call_args[0] == "user-1"
            assert call_args[1] == {"key": "value"}
            # Check keyword args for session_id and run_id
            call_kwargs = service.config_resolver.resolve.call_args[1]
            assert call_kwargs["session_id"] == "sess-1"
            assert call_kwargs["run_id"] == "123"

        asyncio.run(run_test())

    def test_handle_claim_stages_skills(self) -> None:
        """Test SkillStager.stage_skills is called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {"skill1": {}, "skill2": {"enabled": True}},
                }
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.skill_stager.stage_skills.assert_called_once()
            call_kwargs = service.skill_stager.stage_skills.call_args[1]
            assert call_kwargs["user_id"] == "user-1"
            assert call_kwargs["session_id"] == "sess-1"

        asyncio.run(run_test())

    def test_handle_claim_stages_plugins(self) -> None:
        """Test PluginStager.stage_plugins is called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {},
                    "plugin_files": {"plugin1": {}},
                }
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.plugin_stager.stage_plugins.assert_called_once()

        asyncio.run(run_test())

    def test_handle_claim_stages_inputs(self) -> None:
        """Test AttachmentStager.stage_inputs is called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {},
                    "input_files": [{"path": "/tmp/file.txt"}],
                }
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.attachment_stager.stage_inputs.assert_called_once()

        asyncio.run(run_test())

    def test_handle_claim_resolves_and_stages_slash_commands(self) -> None:
        """Test BackendClient.resolve_slash_commands and SlashCommandStager are called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {"skill1": {}},
                }
            )
            service.backend_client.resolve_slash_commands = AsyncMock(
                return_value=[{"name": "cmd1"}]
            )
            service.slash_command_stager.stage_commands = MagicMock(
                return_value=[{"name": "cmd1", "staged": True}]
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.backend_client.resolve_slash_commands.assert_called_once()
            service.slash_command_stager.stage_commands.assert_called_once()

        asyncio.run(run_test())

    def test_handle_claim_stages_claude_md_enabled(self) -> None:
        """Test ClaudeMdStager.stage is called with enabled=True."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.backend_client.get_claude_md = AsyncMock(
                return_value={
                    "enabled": True,
                    "content": "test instructions",
                }
            )
            service.claude_md_stager.stage = MagicMock(
                return_value={"enabled": True, "bytes": 100}
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.backend_client.get_claude_md.assert_called_once()
            service.claude_md_stager.stage.assert_called_once()
            call_kwargs = service.claude_md_stager.stage.call_args[1]
            assert call_kwargs["enabled"] is True
            assert call_kwargs["content"] == "test instructions"

        asyncio.run(run_test())

    def test_handle_claim_claude_md_exception_handled(self) -> None:
        """Test ClaudeMdStager exception is caught and logged (lines 379-383)."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.backend_client.get_claude_md = AsyncMock(
                side_effect=Exception("CLAUDE.md fetch failed")
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            # Should not raise, just log warning
            await service._handle_claim(claim)

        asyncio.run(run_test())

    def test_handle_claim_stages_subagents(self) -> None:
        """Test SubAgentStager.stage_raw_agents is called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {},
                    "subagent_raw_agents": {"agent1": {"type": "researcher"}},
                }
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.subagent_stager.stage_raw_agents.assert_called_once()

        asyncio.run(run_test())

    def test_handle_claim_subagent_exception_handled(self) -> None:
        """Test SubAgentStager exception is caught and logged (lines 404-408)."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            service.config_resolver.resolve = AsyncMock(
                return_value={
                    "skill_files": {},
                    "subagent_raw_agents": {"agent1": {}},
                }
            )
            service.subagent_stager.stage_raw_agents = MagicMock(
                side_effect=Exception("Subagent staging failed")
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            # Should not raise, just log warning
            await service._handle_claim(claim)

        asyncio.run(run_test())

    def test_handle_claim_uses_container_mode_from_config(self) -> None:
        """Test container_mode is read from config_snapshot."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            # Mock container_pool
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {
                    "container_mode": "persistent",
                    "container_id": "existing-id",
                },
            }

            await service._handle_claim(claim)

            mock_pool.get_or_create_container.assert_called_once()
            call_kwargs = mock_pool.get_or_create_container.call_args[1]
            assert call_kwargs["container_mode"] == "persistent"
            assert call_kwargs["container_id"] == "existing-id"

        asyncio.run(run_test())

    def test_handle_claim_executor_execute_task_called(self) -> None:
        """Test ExecutorClient.execute_task is called with correct params."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool

            claim = {
                "run": {"run_id": 42, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test prompt",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.executor_client.execute_task.assert_called_once()
            call_kwargs = service.executor_client.execute_task.call_args[1]
            assert call_kwargs["executor_url"] == "http://executor:8080"
            assert call_kwargs["session_id"] == "sess-1"
            assert call_kwargs["run_id"] == "42"
            assert call_kwargs["prompt"] == "test prompt"
            assert call_kwargs["callback_token"] == "test-token"

        asyncio.run(run_test())

    def test_handle_claim_backend_start_run_called(self) -> None:
        """Test BackendClient.start_run is called."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.backend_client.start_run.assert_called_once()
            call_kwargs = service.backend_client.start_run.call_args[1]
            assert call_kwargs["run_id"] == 1
            assert call_kwargs["worker_id"] == service.worker_id

        asyncio.run(run_test())

    def test_handle_claim_start_run_exception_handled(self) -> None:
        """Test BackendClient.start_run exception is caught (lines 472-473)."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool
            service.backend_client.start_run = AsyncMock(
                side_effect=Exception("Start run failed")
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            # Should not raise, just log error
            await service._handle_claim(claim)

        asyncio.run(run_test())

    def test_handle_claim_releases_inflight_run_on_success(self) -> None:
        """Test run is released from inflight set after success."""

        async def run_test() -> None:
            service = self._create_service_with_all_deps()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool

            claim = {
                "run": {"run_id": "run-123", "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            # Run should be released in finally block
            assert "run-123" not in service._inflight_run_ids

        asyncio.run(run_test())

    def test_handle_claim_creates_container_pool_when_none(self) -> None:
        """Test container_pool is created via TaskDispatcher when None (line 413)."""

        async def run_test() -> None:
            with (
                patch("app.services.run_pull_service.get_settings") as mock_settings,
                patch(
                    "app.services.run_pull_service.BackendClient"
                ) as mock_backend_cls,
                patch(
                    "app.services.run_pull_service.ExecutorClient"
                ) as mock_executor_cls,
                patch(
                    "app.services.run_pull_service.ConfigResolver"
                ) as mock_resolver_cls,
                patch("app.services.run_pull_service.SkillStager"),
                patch("app.services.run_pull_service.PluginStager"),
                patch("app.services.run_pull_service.AttachmentStager"),
                patch("app.services.run_pull_service.ClaudeMdStager"),
                patch("app.services.run_pull_service.SlashCommandStager"),
                patch("app.services.run_pull_service.SubAgentStager"),
                patch(
                    "app.services.run_pull_service.TaskDispatcher.get_container_pool"
                ) as mock_get_pool,
            ):
                mock_settings.return_value = MagicMock(
                    max_concurrent_tasks=5,
                    task_claim_lease_seconds=30,
                    callback_base_url="http://test.local",
                    callback_token="test-token",
                )

                mock_backend = MagicMock()
                mock_backend.resolve_slash_commands = AsyncMock(return_value=[])
                mock_backend.get_claude_md = AsyncMock(return_value={})
                mock_backend.start_run = AsyncMock()
                mock_backend_cls.return_value = mock_backend

                mock_executor = MagicMock()
                mock_executor.execute_task = AsyncMock()
                mock_executor_cls.return_value = mock_executor

                mock_resolver = MagicMock()
                mock_resolver.resolve = AsyncMock(return_value={"skill_files": {}})
                mock_resolver_cls.return_value = mock_resolver

                # Mock container pool returned by TaskDispatcher
                mock_pool = MagicMock()
                mock_pool.get_or_create_container = AsyncMock(
                    return_value=("http://executor:8080", "container-123")
                )
                mock_get_pool.return_value = mock_pool

                service = RunPullService()
                # container_pool starts as None, so get_container_pool will be called
                assert service.container_pool is None

                claim = {
                    "run": {"run_id": 1, "session_id": "sess-1"},
                    "user_id": "user-1",
                    "prompt": "test",
                    "config_snapshot": {},
                }

                await service._handle_claim(claim)

                # TaskDispatcher.get_container_pool should have been called
                mock_get_pool.assert_called_once()
                # container_pool should now be set
                assert service.container_pool is mock_pool

        asyncio.run(run_test())


class TestHandleClaimExceptionHandling(unittest.TestCase):
    """Test RunPullService._handle_claim exception handling (lines 487-507)."""

    def _create_service_for_exception_test(self) -> RunPullService:
        """Create service with all dependencies for exception testing."""
        with (
            patch("app.services.run_pull_service.get_settings") as mock_settings,
            patch("app.services.run_pull_service.BackendClient") as mock_backend_cls,
            patch("app.services.run_pull_service.ExecutorClient") as mock_executor_cls,
            patch("app.services.run_pull_service.ConfigResolver") as mock_resolver_cls,
            patch("app.services.run_pull_service.SkillStager"),
            patch("app.services.run_pull_service.PluginStager"),
            patch("app.services.run_pull_service.AttachmentStager"),
            patch("app.services.run_pull_service.ClaudeMdStager"),
            patch("app.services.run_pull_service.SlashCommandStager"),
            patch("app.services.run_pull_service.SubAgentStager"),
        ):
            mock_settings.return_value = MagicMock(
                max_concurrent_tasks=5,
                task_claim_lease_seconds=30,
                callback_base_url="http://test.local",
                callback_token="test-token",
            )

            mock_backend = MagicMock()
            mock_backend.resolve_slash_commands = AsyncMock(return_value=[])
            mock_backend.get_claude_md = AsyncMock(return_value={})
            mock_backend.fail_run = AsyncMock()
            mock_backend_cls.return_value = mock_backend

            mock_executor = MagicMock()
            mock_executor.execute_task = AsyncMock()
            mock_executor_cls.return_value = mock_executor

            mock_resolver = MagicMock()
            mock_resolver.resolve = AsyncMock(return_value={"skill_files": {}})
            mock_resolver_cls.return_value = mock_resolver

            return RunPullService()

    def test_handle_claim_exception_logs_and_fails_run(self) -> None:
        """Test exception causes fail_run to be called (lines 487-498)."""

        async def run_test() -> None:
            service = self._create_service_for_exception_test()
            service.config_resolver.resolve = AsyncMock(
                side_effect=RuntimeError("Config resolution failed")
            )

            claim = {
                "run": {"run_id": 999, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            # fail_run should be called
            service.backend_client.fail_run.assert_called_once()
            call_kwargs = service.backend_client.fail_run.call_args[1]
            assert call_kwargs["run_id"] == 999
            assert "Config resolution failed" in call_kwargs["error_message"]

        asyncio.run(run_test())

    def test_handle_claim_fail_run_exception_handled(self) -> None:
        """Test fail_run exception is caught (lines 497-498)."""

        async def run_test() -> None:
            service = self._create_service_for_exception_test()
            service.config_resolver.resolve = AsyncMock(
                side_effect=RuntimeError("Config failed")
            )
            service.backend_client.fail_run = AsyncMock(
                side_effect=Exception("Fail run also failed")
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            # Should not raise, both exceptions are logged
            await service._handle_claim(claim)

        asyncio.run(run_test())

    def test_handle_claim_releases_inflight_run_on_exception(self) -> None:
        """Test run is released from inflight set after exception."""

        async def run_test() -> None:
            service = self._create_service_for_exception_test()
            service.config_resolver.resolve = AsyncMock(
                side_effect=RuntimeError("Failed")
            )

            claim = {
                "run": {"run_id": "run-xyz", "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            # Run should be released in finally block
            assert "run-xyz" not in service._inflight_run_ids

        asyncio.run(run_test())

    def test_handle_claim_executor_exception_fails_run(self) -> None:
        """Test ExecutorClient exception causes fail_run."""

        async def run_test() -> None:
            service = self._create_service_for_exception_test()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                return_value=("http://executor:8080", "container-123")
            )
            service.container_pool = mock_pool
            service.executor_client.execute_task = AsyncMock(
                side_effect=ConnectionError("Executor unreachable")
            )

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.backend_client.fail_run.assert_called_once()

        asyncio.run(run_test())

    def test_handle_claim_container_pool_exception_fails_run(self) -> None:
        """Test container_pool exception causes fail_run."""

        async def run_test() -> None:
            service = self._create_service_for_exception_test()
            mock_pool = MagicMock()
            mock_pool.get_or_create_container = AsyncMock(
                side_effect=RuntimeError("No containers available")
            )
            service.container_pool = mock_pool

            claim = {
                "run": {"run_id": 1, "session_id": "sess-1"},
                "user_id": "user-1",
                "prompt": "test",
                "config_snapshot": {},
            }

            await service._handle_claim(claim)

            service.backend_client.fail_run.assert_called_once()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
