"""Tests for app/scheduler/pull_job_registry.py."""

import unittest
from unittest.mock import MagicMock

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class TestRegisterPullJobs(unittest.TestCase):
    """Test register_pull_jobs function."""

    def _create_mock_scheduler(self) -> AsyncIOScheduler:
        """Create a mock APScheduler."""
        mock_scheduler = MagicMock(spec=AsyncIOScheduler)
        mock_scheduler.add_job = MagicMock()
        return mock_scheduler

    def _create_mock_pull_service(self) -> MagicMock:
        """Create a mock RunPullService."""
        mock_service = MagicMock()
        mock_service.poll = MagicMock()
        mock_service.open_window = MagicMock()
        mock_service.poll_window = MagicMock()
        mock_service.set_window_until = MagicMock()
        return mock_service

    def test_register_returns_empty_list_when_disabled(self) -> None:
        """Test that register returns empty list when config is disabled."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import PullScheduleConfig

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(enabled=False, rules=[])

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert result == []
        mock_scheduler.add_job.assert_not_called()

    def test_register_interval_rule(self) -> None:
        """Test registering an interval pull rule."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="test-interval",
                    enabled=True,
                    schedule_modes=["immediate"],
                    seconds=5,
                    start_immediately=True,
                )
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert len(result) == 1
        assert result[0] == "pull-test-interval"
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["seconds"] == 5
        assert call_kwargs["id"] == "pull-test-interval"
        assert call_kwargs["kwargs"]["schedule_modes"] == ["immediate"]

    def test_register_interval_rule_clamps_seconds_to_min_1(self) -> None:
        """Test that interval seconds is clamped to min 1."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="test-interval",
                    enabled=True,
                    seconds=0,  # Should be clamped to 1
                )
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert len(result) == 1
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs["seconds"] == 1

    def test_register_interval_rule_without_start_immediately(self) -> None:
        """Test interval rule without start_immediately."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="test-interval",
                    enabled=True,
                    seconds=10,
                    start_immediately=False,
                )
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert len(result) == 1
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs["next_run_time"] is None

    def test_register_skips_disabled_rule(self) -> None:
        """Test that disabled rules are skipped."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="disabled-rule",
                    enabled=False,
                    seconds=5,
                )
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert result == []
        mock_scheduler.add_job.assert_not_called()

    def test_register_window_rule(self) -> None:
        """Test registering a window pull rule."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            PullScheduleConfig,
            WindowPullRule,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                WindowPullRule(
                    id="test-window",
                    enabled=True,
                    schedule_modes=["nightly"],
                    cron={"hour": 2, "minute": 0},
                    window_minutes=60,
                    poll_interval_seconds=5,
                )
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        assert len(result) == 2
        assert "pull-test-window-open" in result
        assert "pull-test-window-poll" in result
        assert mock_scheduler.add_job.call_count == 2

    def test_register_window_rule_with_bootstrap(self) -> None:
        """Test window rule with bootstrap window."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            PullScheduleConfig,
            WindowPullRule,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        # Create a rule that would be in a bootstrap window
        # Use cron that fires every minute to ensure we're in a window
        config = PullScheduleConfig(
            enabled=True,
            rules=[
                WindowPullRule(
                    id="test-window",
                    enabled=True,
                    cron={"minute": "*"},  # Every minute
                    window_minutes=60,
                    poll_interval_seconds=5,
                    bootstrap_lookback_hours=1,
                )
            ],
        )

        register_pull_jobs(mock_scheduler, mock_service, config)

        # Should have called set_window_until due to bootstrap
        mock_service.set_window_until.assert_called()

    def test_register_multiple_rules(self) -> None:
        """Test registering multiple rules."""
        from app.scheduler.pull_job_registry import register_pull_jobs
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
            WindowPullRule,
        )

        mock_scheduler = self._create_mock_scheduler()
        mock_service = self._create_mock_pull_service()

        config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(id="interval-1", enabled=True, seconds=5),
                WindowPullRule(
                    id="window-1",
                    enabled=True,
                    cron={"hour": 2},
                    window_minutes=60,
                ),
            ],
        )

        result = register_pull_jobs(mock_scheduler, mock_service, config)

        # 1 interval job + 2 window jobs = 3 total
        assert len(result) == 3
        assert mock_scheduler.add_job.call_count == 3


class TestUnregisterPullJobs(unittest.TestCase):
    """Test unregister_pull_jobs function."""

    def test_unregister_removes_all_jobs(self) -> None:
        """Test that unregister removes all jobs."""
        from app.scheduler.pull_job_registry import unregister_pull_jobs

        mock_scheduler = MagicMock()
        mock_scheduler.remove_job = MagicMock()

        job_ids = ["job-1", "job-2", "job-3"]
        unregister_pull_jobs(mock_scheduler, job_ids)

        assert mock_scheduler.remove_job.call_count == 3

    def test_unregister_handles_exception(self) -> None:
        """Test that unregister handles exceptions gracefully."""
        from app.scheduler.pull_job_registry import unregister_pull_jobs

        mock_scheduler = MagicMock()
        mock_scheduler.remove_job = MagicMock(side_effect=Exception("Job not found"))

        # Should not raise
        unregister_pull_jobs(mock_scheduler, ["job-1", "job-2"])

        assert mock_scheduler.remove_job.call_count == 2

    def test_unregister_empty_list(self) -> None:
        """Test unregister with empty list."""
        from app.scheduler.pull_job_registry import unregister_pull_jobs

        mock_scheduler = MagicMock()
        mock_scheduler.remove_job = MagicMock()

        unregister_pull_jobs(mock_scheduler, [])

        mock_scheduler.remove_job.assert_not_called()


if __name__ == "__main__":
    unittest.main()
