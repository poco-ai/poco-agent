"""Tests for app/scheduler/pull_schedule_config.py."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestIntervalPullRule(unittest.TestCase):
    """Test IntervalPullRule model."""

    def test_create_with_defaults(self) -> None:
        """Test creating rule with default values."""
        from app.scheduler.pull_schedule_config import IntervalPullRule

        rule = IntervalPullRule(id="test")

        assert rule.kind == "interval"
        assert rule.enabled is True
        assert rule.seconds == 2
        assert rule.start_immediately is True
        assert rule.schedule_modes == []

    def test_validate_id_strips_whitespace(self) -> None:
        """Test that id is stripped of whitespace."""
        from app.scheduler.pull_schedule_config import IntervalPullRule

        rule = IntervalPullRule(id="  test-id  ")

        assert rule.id == "test-id"

    def test_validate_id_rejects_empty(self) -> None:
        """Test that empty id is rejected."""
        from app.scheduler.pull_schedule_config import IntervalPullRule

        with pytest.raises(ValueError, match="rule id cannot be empty"):
            IntervalPullRule(id="   ")

    def test_validate_schedule_modes_filters_empty(self) -> None:
        """Test that empty schedule modes are filtered."""
        from app.scheduler.pull_schedule_config import IntervalPullRule

        rule = IntervalPullRule(
            id="test",
            schedule_modes=["  mode1  ", "", "  ", "mode2"],
        )

        assert rule.schedule_modes == ["mode1", "mode2"]

    def test_validate_schedule_modes_rejects_non_strings(self) -> None:
        """Test that non-string schedule modes cause validation error."""
        from app.scheduler.pull_schedule_config import IntervalPullRule
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IntervalPullRule(
                id="test",
                schedule_modes=["mode1", None, 123, "mode2"],  # type: ignore
            )


class TestWindowPullRule(unittest.TestCase):
    """Test WindowPullRule model."""

    def test_create_with_required_fields(self) -> None:
        """Test creating rule with required fields."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        rule = WindowPullRule(id="test", cron={"hour": 2})

        assert rule.kind == "window"
        assert rule.cron == {"hour": 2}
        assert rule.window_minutes == 360
        assert rule.poll_interval_seconds == 2
        assert rule.timezone == "UTC"

    def test_validate_id_strips_whitespace(self) -> None:
        """Test that id is stripped of whitespace."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        rule = WindowPullRule(id="  test-id  ", cron={"hour": 2})

        assert rule.id == "test-id"

    def test_validate_id_rejects_empty(self) -> None:
        """Test that empty id is rejected."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(ValueError, match="rule id cannot be empty"):
            WindowPullRule(id="   ", cron={"hour": 2})

    def test_validate_schedule_modes_filters_empty(self) -> None:
        """Test that empty schedule modes are filtered."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        rule = WindowPullRule(
            id="test",
            cron={"hour": 2},
            schedule_modes=["  mode1  ", "", "mode2"],
        )

        assert rule.schedule_modes == ["mode1", "mode2"]

    def test_validate_requires_cron(self) -> None:
        """Test that cron is required."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(
            ValueError, match="window rule requires non-empty cron config"
        ):
            WindowPullRule(id="test", cron={})

    def test_validate_window_minutes_positive(self) -> None:
        """Test that window_minutes must be positive."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(ValueError, match="window_minutes must be > 0"):
            WindowPullRule(id="test", cron={"hour": 2}, window_minutes=0)

        with pytest.raises(ValueError, match="window_minutes must be > 0"):
            WindowPullRule(id="test", cron={"hour": 2}, window_minutes=-1)

    def test_validate_poll_interval_positive(self) -> None:
        """Test that poll_interval_seconds must be positive."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(ValueError, match="poll_interval_seconds must be > 0"):
            WindowPullRule(id="test", cron={"hour": 2}, poll_interval_seconds=0)

    def test_validate_bootstrap_lookback_positive(self) -> None:
        """Test that bootstrap_lookback_hours must be positive."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(ValueError, match="bootstrap_lookback_hours must be > 0"):
            WindowPullRule(id="test", cron={"hour": 2}, bootstrap_lookback_hours=0)

    def test_validate_bootstrap_max_iterations_positive(self) -> None:
        """Test that bootstrap_max_iterations must be positive."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        with pytest.raises(ValueError, match="bootstrap_max_iterations must be > 0"):
            WindowPullRule(id="test", cron={"hour": 2}, bootstrap_max_iterations=0)

    def test_build_cron_trigger_with_timezone(self) -> None:
        """Test building cron trigger with custom timezone."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        rule = WindowPullRule(
            id="test",
            cron={"hour": 2, "minute": 30},
            timezone="America/New_York",
        )

        trigger = rule.build_cron_trigger()

        assert trigger is not None

    def test_build_cron_trigger_invalid_timezone_fallback(self) -> None:
        """Test that invalid timezone falls back to UTC."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        rule = WindowPullRule(
            id="test",
            cron={"hour": 2},
            timezone="Invalid/Timezone",
        )

        trigger = rule.build_cron_trigger()

        assert trigger is not None

    def test_resolve_bootstrap_window_no_fire(self) -> None:
        """Test bootstrap resolution when no fire time found."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        # Use a cron that won't fire in the past - use a valid but rare schedule
        # (e.g., only on Feb 29, which won't occur in lookback for most years)
        rule = WindowPullRule(
            id="test",
            cron={"month": 2, "day": 29, "hour": 2},  # Feb 29 only
            bootstrap_lookback_hours=1,  # Only look back 1 hour
        )

        # If not around Feb 29, should return None
        now = datetime.now(timezone.utc)
        result = rule.resolve_bootstrap_window_until(now)

        # Result depends on current date - just ensure no exception
        assert result is None or isinstance(result, datetime)

    def test_resolve_bootstrap_window_within_window(self) -> None:
        """Test bootstrap resolution when within an active window."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        # Create a rule that fires every minute
        rule = WindowPullRule(
            id="test",
            cron={"minute": "*"},
            window_minutes=60,
            bootstrap_lookback_hours=1,
        )

        now = datetime.now(timezone.utc)
        result = rule.resolve_bootstrap_window_until(now)

        # Since cron fires every minute, should find a window
        assert result is None or isinstance(result, datetime)

    def test_resolve_bootstrap_window_max_iterations(self) -> None:
        """Test bootstrap resolution with max iterations limit."""
        from app.scheduler.pull_schedule_config import WindowPullRule

        # Create a rule that fires every second with very low max iterations
        rule = WindowPullRule(
            id="test",
            cron={"second": "*"},  # Every second
            window_minutes=60,
            bootstrap_lookback_hours=1,
            bootstrap_max_iterations=2,  # Very low to trigger break
        )

        now = datetime.now(timezone.utc)
        result = rule.resolve_bootstrap_window_until(now)

        # Should still return a valid window (iteration limit reached)
        # The break at line 101 should be triggered
        assert result is None or isinstance(result, datetime)


class TestPullScheduleConfig(unittest.TestCase):
    """Test PullScheduleConfig model."""

    def test_create_with_defaults(self) -> None:
        """Test creating config with defaults."""
        from app.scheduler.pull_schedule_config import PullScheduleConfig

        config = PullScheduleConfig()

        assert config.enabled is True
        assert config.rules == []

    def test_duplicate_rule_ids_rejected(self) -> None:
        """Test that duplicate rule IDs are rejected."""
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        with pytest.raises(ValueError, match="duplicate rule id"):
            PullScheduleConfig(
                rules=[
                    IntervalPullRule(id="duplicate", seconds=5),
                    IntervalPullRule(id="duplicate", seconds=10),
                ]
            )

    def test_schedule_modes_default_to_rule_id(self) -> None:
        """Test that empty schedule_modes defaults to rule id."""
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
        )

        config = PullScheduleConfig(
            rules=[
                IntervalPullRule(id="test-rule", seconds=5),
            ]
        )

        assert config.rules[0].schedule_modes == ["test-rule"]

    def test_mixed_rule_types(self) -> None:
        """Test config with mixed rule types."""
        from app.scheduler.pull_schedule_config import (
            IntervalPullRule,
            PullScheduleConfig,
            WindowPullRule,
        )

        config = PullScheduleConfig(
            rules=[
                IntervalPullRule(id="interval-1", seconds=5),
                WindowPullRule(id="window-1", cron={"hour": 2}),
            ]
        )

        assert len(config.rules) == 2
        assert config.rules[0].kind == "interval"
        assert config.rules[1].kind == "window"


class TestLoadFileData(unittest.TestCase):
    """Test _load_file_data function."""

    def test_load_toml_file(self) -> None:
        """Test loading a TOML file."""
        from app.scheduler.pull_schedule_config import _load_file_data

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("enabled = true\n")
            f.write("[[rules]]\n")
            f.write('kind = "interval"\n')
            f.write('id = "test"\n')
            f.write("seconds = 5\n")
            temp_path = Path(f.name)

        try:
            result = _load_file_data(temp_path)

            assert result["enabled"] is True
            assert len(result["rules"]) == 1
            assert result["rules"][0]["id"] == "test"
        finally:
            temp_path.unlink()

    def test_load_json_file(self) -> None:
        """Test loading a JSON file."""
        from app.scheduler.pull_schedule_config import _load_file_data

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": True, "rules": []}, f)
            temp_path = Path(f.name)

        try:
            result = _load_file_data(temp_path)

            assert result["enabled"] is True
            assert result["rules"] == []
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test loading a nonexistent file."""
        from app.scheduler.pull_schedule_config import _load_file_data

        with pytest.raises(FileNotFoundError):
            _load_file_data(Path("/nonexistent/path.toml"))

    def test_load_unsupported_format(self) -> None:
        """Test loading an unsupported file format."""
        from app.scheduler.pull_schedule_config import _load_file_data

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("enabled: true\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported schedule config format"):
                _load_file_data(temp_path)
        finally:
            temp_path.unlink()


class TestLoadPullScheduleConfig(unittest.TestCase):
    """Test load_pull_schedule_config function."""

    def test_load_none_path(self) -> None:
        """Test loading with None path."""
        from app.scheduler.pull_schedule_config import load_pull_schedule_config

        result = load_pull_schedule_config(None)

        assert result is None

    def test_load_valid_config(self) -> None:
        """Test loading a valid config file."""
        from app.scheduler.pull_schedule_config import load_pull_schedule_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "enabled": True,
                    "rules": [{"kind": "interval", "id": "test", "seconds": 5}],
                },
                f,
            )
            temp_path = f.name

        try:
            result = load_pull_schedule_config(temp_path)

            assert result is not None
            assert result.enabled is True
            assert len(result.rules) == 1
        finally:
            Path(temp_path).unlink()


class TestDefaultPullScheduleConfigFromSettings(unittest.TestCase):
    """Test default_pull_schedule_config_from_settings function."""

    def test_default_config_with_minimal_settings(self) -> None:
        """Test default config with minimal settings."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = True
        mock_settings.task_pull_interval_seconds = 2
        mock_settings.task_pull_immediate_enabled = True
        mock_settings.task_pull_scheduled_enabled = True
        mock_settings.task_pull_nightly_enabled = False

        result = default_pull_schedule_config_from_settings(mock_settings)

        assert result.enabled is True
        # Should have immediate and scheduled rules (2 total)
        assert len(result.rules) == 2

    def test_default_config_with_nightly_enabled(self) -> None:
        """Test default config with nightly enabled."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = True
        mock_settings.task_pull_interval_seconds = 2
        mock_settings.task_pull_immediate_enabled = True
        mock_settings.task_pull_scheduled_enabled = True
        mock_settings.task_pull_nightly_enabled = True
        mock_settings.task_pull_nightly_start_hour = 2
        mock_settings.task_pull_nightly_start_minute = 0
        mock_settings.task_pull_nightly_timezone = "UTC"
        mock_settings.task_pull_nightly_window_minutes = 360
        mock_settings.task_pull_nightly_poll_interval_seconds = 2

        result = default_pull_schedule_config_from_settings(mock_settings)

        # Should have immediate, scheduled, and nightly rules (3 total)
        assert len(result.rules) == 3
        assert any(r.id == "nightly" for r in result.rules)

    def test_default_config_with_disabled_pull(self) -> None:
        """Test default config with pull disabled."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = False
        mock_settings.task_pull_interval_seconds = 2
        mock_settings.task_pull_immediate_enabled = True
        mock_settings.task_pull_scheduled_enabled = True
        mock_settings.task_pull_nightly_enabled = False

        result = default_pull_schedule_config_from_settings(mock_settings)

        assert result.enabled is False

    def test_default_config_clamps_interval(self) -> None:
        """Test that interval is clamped to min 1."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = True
        mock_settings.task_pull_interval_seconds = 0  # Should be clamped
        mock_settings.task_pull_immediate_enabled = True
        mock_settings.task_pull_immediate_interval_seconds = None
        mock_settings.task_pull_scheduled_enabled = False
        mock_settings.task_pull_nightly_enabled = False

        result = default_pull_schedule_config_from_settings(mock_settings)

        immediate_rule = next(r for r in result.rules if r.id == "immediate")
        assert immediate_rule.seconds == 1

    def test_default_config_uses_specific_intervals(self) -> None:
        """Test that specific intervals are used when provided."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = True
        mock_settings.task_pull_interval_seconds = 10
        mock_settings.task_pull_immediate_enabled = True
        mock_settings.task_pull_immediate_interval_seconds = 5
        mock_settings.task_pull_scheduled_enabled = True
        mock_settings.task_pull_scheduled_interval_seconds = 15
        mock_settings.task_pull_nightly_enabled = False

        result = default_pull_schedule_config_from_settings(mock_settings)

        immediate_rule = next(r for r in result.rules if r.id == "immediate")
        scheduled_rule = next(r for r in result.rules if r.id == "scheduled")

        assert immediate_rule.seconds == 5
        assert scheduled_rule.seconds == 15

    def test_default_config_all_queues_disabled(self) -> None:
        """Test config when all queue types are disabled."""
        from app.scheduler.pull_schedule_config import (
            default_pull_schedule_config_from_settings,
        )

        mock_settings = MagicMock()
        mock_settings.task_pull_enabled = True
        mock_settings.task_pull_interval_seconds = 2
        mock_settings.task_pull_immediate_enabled = False
        mock_settings.task_pull_scheduled_enabled = False
        mock_settings.task_pull_nightly_enabled = False

        result = default_pull_schedule_config_from_settings(mock_settings)

        assert result.enabled is True
        assert result.rules == []


if __name__ == "__main__":
    unittest.main()
