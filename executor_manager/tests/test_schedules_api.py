"""Tests for app/api/v1/schedules.py."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestGetSchedules(unittest.TestCase):
    """Test GET /api/v1/schedules endpoint."""

    def test_get_schedules_with_current_config(self) -> None:
        """Test get schedules with current config already set."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="test-rule",
                    enabled=True,
                    seconds=5,
                    schedule_modes=["test"],
                )
            ],
        )

        with patch(
            "app.api.v1.schedules.get_current_pull_schedule_config",
            return_value=mock_config,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "rules" in data["data"]
            assert len(data["data"]["rules"]) == 1
            assert data["data"]["rules"][0]["id"] == "test-rule"
            assert data["data"]["rules"][0]["kind"] == "interval"

    def test_get_schedules_with_window_rule(self) -> None:
        """Test get schedules with window rule."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            PullScheduleConfig,
            WindowPullRule,
        )

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                WindowPullRule(
                    id="nightly",
                    enabled=True,
                    cron={"hour": 2, "minute": 0},
                    window_minutes=60,
                    schedule_modes=["nightly"],
                )
            ],
        )

        with patch(
            "app.api.v1.schedules.get_current_pull_schedule_config",
            return_value=mock_config,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["rules"]) == 1
            rule = data["data"]["rules"][0]
            assert rule["id"] == "nightly"
            assert rule["kind"] == "window"
            assert rule["cron"] == {"hour": 2, "minute": 0}
            assert rule["window_minutes"] == 60

    def test_get_schedules_config_disabled(self) -> None:
        """Test get schedules when config is disabled."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_config = PullScheduleConfig(
            enabled=False,
            rules=[
                IntervalPullRule(
                    id="disabled-rule",
                    enabled=True,
                    seconds=5,
                )
            ],
        )

        with patch(
            "app.api.v1.schedules.get_current_pull_schedule_config",
            return_value=mock_config,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            # Rule should be marked as disabled (effective_enabled = False)
            assert data["data"]["rules"][0]["enabled"] is False

    def test_get_schedules_rule_disabled(self) -> None:
        """Test get schedules when individual rule is disabled."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="disabled-rule",
                    enabled=False,
                    seconds=5,
                )
            ],
        )

        with patch(
            "app.api.v1.schedules.get_current_pull_schedule_config",
            return_value=mock_config,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rules"][0]["enabled"] is False

    def test_get_schedules_no_current_config_uses_settings(self) -> None:
        """Test get schedules loads config from settings when no current config."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="from-settings",
                    enabled=True,
                    seconds=10,
                )
            ],
        )

        with (
            patch(
                "app.api.v1.schedules.get_current_pull_schedule_config",
                return_value=None,
            ),
            patch(
                "app.api.v1.schedules.load_pull_schedule_config",
                return_value=None,
            ),
            patch(
                "app.api.v1.schedules.default_pull_schedule_config_from_settings",
                return_value=mock_config,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rules"][0]["id"] == "from-settings"

    def test_get_schedules_uses_loaded_config(self) -> None:
        """Test get schedules uses loaded config from file."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="from-file",
                    enabled=True,
                    seconds=15,
                )
            ],
        )

        with (
            patch(
                "app.api.v1.schedules.get_current_pull_schedule_config",
                return_value=None,
            ),
            patch(
                "app.api.v1.schedules.load_pull_schedule_config",
                return_value=mock_config,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rules"][0]["id"] == "from-file"

    def test_get_schedules_with_job_info(self) -> None:
        """Test get schedules includes job info."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )
        from datetime import datetime, timezone

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                IntervalPullRule(
                    id="with-job",
                    enabled=True,
                    seconds=5,
                )
            ],
        )

        mock_job = MagicMock()
        mock_job.trigger = "interval[0:00:05]"
        mock_job.next_run_time = datetime.now(timezone.utc)

        with (
            patch(
                "app.api.v1.schedules.get_current_pull_schedule_config",
                return_value=mock_config,
            ),
            patch(
                "app.api.v1.schedules.scheduler.get_job",
                return_value=mock_job,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            # Should have job info
            assert len(data["data"]["rules"][0]["jobs"]) == 1
            assert data["data"]["rules"][0]["jobs"][0]["job_id"] == "pull-with-job"

    def test_get_schedules_window_rule_with_jobs(self) -> None:
        """Test get schedules with window rule includes both jobs."""
        from app.main import app
        from app.scheduler.pull_schedule_config import (
            PullScheduleConfig,
            WindowPullRule,
        )
        from datetime import datetime, timezone

        mock_config = PullScheduleConfig(
            enabled=True,
            rules=[
                WindowPullRule(
                    id="window-job",
                    enabled=True,
                    cron={"hour": 2},
                    window_minutes=60,
                )
            ],
        )

        mock_job = MagicMock()
        mock_job.trigger = "cron[hour='2']"
        mock_job.next_run_time = datetime.now(timezone.utc)

        with (
            patch(
                "app.api.v1.schedules.get_current_pull_schedule_config",
                return_value=mock_config,
            ),
            patch(
                "app.api.v1.schedules.scheduler.get_job",
                return_value=mock_job,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            # Window rule should have two jobs (open and poll)
            assert len(data["data"]["rules"][0]["jobs"]) == 2

    def test_get_schedules_empty_rules(self) -> None:
        """Test get schedules with no rules."""
        from app.main import app
        from app.scheduler.pull_schedule_config import PullScheduleConfig

        mock_config = PullScheduleConfig(enabled=True, rules=[])

        with patch(
            "app.api.v1.schedules.get_current_pull_schedule_config",
            return_value=mock_config,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/schedules")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rules"] == []


class TestBuildJobInfo(unittest.TestCase):
    """Test _build_job_info helper function."""

    def test_returns_none_when_job_not_found(self) -> None:
        """Test returns None when job doesn't exist."""
        from app.api.v1.schedules import _build_job_info

        with patch(
            "app.api.v1.schedules.scheduler.get_job",
            return_value=None,
        ):
            result = _build_job_info("nonexistent-job")
            assert result is None

    def test_returns_job_info_when_found(self) -> None:
        """Test returns job info when job exists."""
        from app.api.v1.schedules import _build_job_info
        from datetime import datetime, timezone

        mock_job = MagicMock()
        mock_job.trigger = "interval[0:00:05]"
        mock_job.next_run_time = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)

        with patch(
            "app.api.v1.schedules.scheduler.get_job",
            return_value=mock_job,
        ):
            result = _build_job_info("test-job")

            assert result is not None
            assert result.job_id == "test-job"
            assert result.trigger == "interval[0:00:05]"
            assert result.next_run_time is not None


if __name__ == "__main__":
    unittest.main()
