"""Tests for app/core/observability/logging.py."""

import logging
import os
import tempfile
import unittest
from unittest.mock import patch


class TestEnvBool(unittest.TestCase):
    """Test _env_bool helper function."""

    def setUp(self) -> None:
        # Clean up any existing env var
        os.environ.pop("TEST_BOOL_VAR", None)

    def tearDown(self) -> None:
        os.environ.pop("TEST_BOOL_VAR", None)

    def test_returns_default_when_not_set(self) -> None:
        """Test returns default when env var is not set."""
        from app.core.observability.logging import _env_bool

        assert _env_bool("TEST_BOOL_VAR", True) is True
        assert _env_bool("TEST_BOOL_VAR", False) is False

    def test_returns_true_for_truthy_values(self) -> None:
        """Test returns True for truthy string values."""
        from app.core.observability.logging import _env_bool

        truthy_values = [
            "1",
            "true",
            "True",
            "TRUE",
            "yes",
            "Yes",
            "YES",
            "y",
            "Y",
            "on",
            "ON",
        ]
        for val in truthy_values:
            os.environ["TEST_BOOL_VAR"] = val
            assert _env_bool("TEST_BOOL_VAR", False) is True, f"Failed for {val}"

    def test_returns_false_for_falsy_values(self) -> None:
        """Test returns False for falsy string values."""
        from app.core.observability.logging import _env_bool

        falsy_values = ["0", "false", "False", "no", "No", "off", "random", ""]
        for val in falsy_values:
            os.environ["TEST_BOOL_VAR"] = val
            assert _env_bool("TEST_BOOL_VAR", True) is False, f"Failed for {val}"


class TestEnvInt(unittest.TestCase):
    """Test _env_int helper function."""

    def setUp(self) -> None:
        os.environ.pop("TEST_INT_VAR", None)

    def tearDown(self) -> None:
        os.environ.pop("TEST_INT_VAR", None)

    def test_returns_default_when_not_set(self) -> None:
        """Test returns default when env var is not set."""
        from app.core.observability.logging import _env_int

        assert _env_int("TEST_INT_VAR", 42) == 42

    def test_parses_valid_integer(self) -> None:
        """Test parses valid integer string."""
        from app.core.observability.logging import _env_int

        os.environ["TEST_INT_VAR"] = "123"
        assert _env_int("TEST_INT_VAR", 0) == 123

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace from value."""
        from app.core.observability.logging import _env_int

        os.environ["TEST_INT_VAR"] = "  456  "
        assert _env_int("TEST_INT_VAR", 0) == 456

    def test_returns_default_for_invalid_value(self) -> None:
        """Test returns default for non-integer value."""
        from app.core.observability.logging import _env_int

        os.environ["TEST_INT_VAR"] = "not_a_number"
        assert _env_int("TEST_INT_VAR", 99) == 99


class TestParseLevel(unittest.TestCase):
    """Test _parse_level helper function."""

    def test_returns_default_for_none(self) -> None:
        """Test returns default for None input."""
        from app.core.observability.logging import _parse_level

        assert _parse_level(None, default=logging.WARNING) == logging.WARNING

    def test_returns_default_for_empty_string(self) -> None:
        """Test returns default for empty string."""
        from app.core.observability.logging import _parse_level

        assert _parse_level("", default=logging.ERROR) == logging.ERROR

    def test_parses_valid_level_names(self) -> None:
        """Test parses valid log level names."""
        from app.core.observability.logging import _parse_level

        assert _parse_level("DEBUG", default=logging.INFO) == logging.DEBUG
        assert _parse_level("info", default=logging.DEBUG) == logging.INFO
        assert _parse_level("WARNING", default=logging.DEBUG) == logging.WARNING
        assert _parse_level("error", default=logging.DEBUG) == logging.ERROR
        assert _parse_level("CRITICAL", default=logging.DEBUG) == logging.CRITICAL

    def test_returns_default_for_invalid_level(self) -> None:
        """Test returns default for invalid level name."""
        from app.core.observability.logging import _parse_level

        assert _parse_level("INVALID", default=logging.INFO) == logging.INFO

    def test_strips_whitespace(self) -> None:
        """Test strips whitespace from level name."""
        from app.core.observability.logging import _parse_level

        assert _parse_level("  DEBUG  ", default=logging.INFO) == logging.DEBUG


class TestSafeValue(unittest.TestCase):
    """Test _safe_value helper function."""

    def test_masks_sensitive_keys(self) -> None:
        """Test that sensitive values are masked."""
        from app.core.observability.logging import _safe_value

        assert _safe_value("token", "secret-value") == '"***"'
        assert _safe_value("SECRET", "secret-value") == '"***"'
        assert _safe_value("password", "my-password") == '"***"'
        assert _safe_value("Authorization", "Bearer xyz") == '"***"'
        assert _safe_value("api_key", "key123") == '"***"'

    def test_formats_none(self) -> None:
        """Test formats None as null."""
        from app.core.observability.logging import _safe_value

        assert _safe_value("value", None) == "null"

    def test_formats_boolean(self) -> None:
        """Test formats boolean values."""
        from app.core.observability.logging import _safe_value

        assert _safe_value("flag", True) == "true"
        assert _safe_value("flag", False) == "false"

    def test_formats_numbers(self) -> None:
        """Test formats numeric values."""
        from app.core.observability.logging import _safe_value

        assert _safe_value("count", 42) == "42"
        assert _safe_value("ratio", 3.14) == "3.14"

    def test_formats_dict_and_list(self) -> None:
        """Test formats dict and list values as JSON."""
        from app.core.observability.logging import _safe_value

        result = _safe_value("data", {"key": "value"})
        assert '"{\\"key\\":\\"value\\"}"' == result

        result = _safe_value("items", [1, 2, 3])
        assert '"[1,2,3]"' in result

    def test_truncates_long_dicts(self) -> None:
        """Test truncates long dict values."""
        from app.core.observability.logging import _safe_value

        long_dict = {f"key{i}": "x" * 200 for i in range(10)}
        result = _safe_value("data", long_dict)
        assert "...(truncated)" in result

    def test_truncates_long_strings(self) -> None:
        """Test truncates long string values."""
        from app.core.observability.logging import _safe_value

        long_string = "x" * 1000
        result = _safe_value("text", long_string)
        assert "...(truncated)" in result

    def test_escapes_newlines(self) -> None:
        """Test escapes newlines in string values."""
        from app.core.observability.logging import _safe_value

        result = _safe_value("message", "line1\nline2")
        assert "\\n" in result


class TestKeyValueFormatter(unittest.TestCase):
    """Test _KeyValueFormatter class."""

    def test_format_time(self) -> None:
        """Test formatTime produces ISO format."""
        from app.core.observability.logging import _KeyValueFormatter

        formatter = _KeyValueFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        result = formatter.formatTime(record)
        assert "T" in result
        assert result.endswith("Z")

    def test_format_basic_message(self) -> None:
        """Test format produces correct output."""
        from app.core.observability.logging import _KeyValueFormatter

        formatter = _KeyValueFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.service = "test-service"
        record.request_id = "req-123"
        record.trace_id = "trace-456"

        result = formatter.format(record)
        assert "INFO" in result
        assert "test-service" in result
        assert "test.logger" in result
        assert "request_id=req-123" in result
        assert "trace_id=trace-456" in result
        assert "test message" in result

    def test_format_with_extras(self) -> None:
        """Test format includes extra fields."""
        from app.core.observability.logging import _KeyValueFormatter

        formatter = _KeyValueFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="message",
            args=(),
            exc_info=None,
        )
        record.service = "test"
        record.request_id = "-"
        record.trace_id = "-"
        record.custom_field = "custom_value"
        record.count = 42

        result = formatter.format(record)
        assert "count=42" in result
        assert "custom_field=" in result


class TestBuildFileHandler(unittest.TestCase):
    """Test _build_file_handler function."""

    def test_returns_none_when_log_to_file_disabled(self) -> None:
        """Test returns None when LOG_TO_FILE is False."""
        from app.core.observability.logging import _build_file_handler

        with patch.dict(os.environ, {"LOG_TO_FILE": "false"}, clear=False):
            result = _build_file_handler(
                service_name="test",
                formatter=logging.Formatter(),
            )
            assert result is None

    def test_creates_file_handler_when_enabled(self) -> None:
        """Test creates file handler when LOG_TO_FILE is True."""
        from app.core.observability.logging import _build_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {"LOG_TO_FILE": "true", "LOG_DIR": tmpdir},
                clear=False,
            ):
                result = _build_file_handler(
                    service_name="test-service",
                    formatter=logging.Formatter(),
                )
                assert result is not None
                assert isinstance(result, logging.Handler)

    def test_uses_custom_log_dir_and_filename(self) -> None:
        """Test uses custom log directory and filename from env."""
        from app.core.observability.logging import _build_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {
                    "LOG_TO_FILE": "true",
                    "LOG_DIR": tmpdir,
                    "LOG_FILE_NAME": "custom.log",
                },
                clear=False,
            ):
                result = _build_file_handler(
                    service_name="test",
                    formatter=logging.Formatter(),
                )
                assert result is not None

    def test_returns_none_on_exception(self) -> None:
        """Test returns None when file handler creation raises exception."""
        from app.core.observability.logging import _build_file_handler

        # Reset logging to avoid record factory conflicts
        logging.setLogRecordFactory(logging.LogRecord)

        with (
            patch.dict(
                os.environ,
                {"LOG_TO_FILE": "true", "LOG_DIR": "/nonexistent/path"},
                clear=False,
            ),
            patch(
                "app.core.observability.logging.TimedRotatingFileHandler",
                side_effect=OSError("Permission denied"),
            ),
            patch(
                "app.core.observability.logging.Path.mkdir",
                side_effect=OSError("Cannot create directory"),
            ),
        ):
            result = _build_file_handler(
                service_name="test",
                formatter=logging.Formatter(),
            )
            assert result is None


class TestConfigureLogging(unittest.TestCase):
    """Test configure_logging function."""

    def test_configures_root_logger(self) -> None:
        """Test configures root logger with handler."""
        from app.core.observability.logging import configure_logging

        # Reset the factory flag
        import app.core.observability.logging as log_module

        log_module._installed_record_factory = False

        configure_logging(debug=False, service_name="test-service", access_log=False)

        root = logging.getLogger()
        assert len(root.handlers) > 0
        assert root.level == logging.INFO

    def test_sets_debug_level(self) -> None:
        """Test sets DEBUG level when debug=True."""
        from app.core.observability.logging import configure_logging

        import app.core.observability.logging as log_module

        log_module._installed_record_factory = False

        with patch.dict(os.environ, {"LOG_LEVEL": ""}, clear=False):
            configure_logging(debug=True, service_name="test", access_log=False)

            root = logging.getLogger()
            assert root.level == logging.DEBUG

    def test_respects_log_level_env(self) -> None:
        """Test respects LOG_LEVEL environment variable."""
        from app.core.observability.logging import configure_logging

        import app.core.observability.logging as log_module

        log_module._installed_record_factory = False

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}, clear=False):
            configure_logging(debug=True, service_name="test", access_log=False)

            root = logging.getLogger()
            assert root.level == logging.WARNING

    def test_uses_env_for_access_log(self) -> None:
        """Test uses UVICORN_ACCESS_LOG env when access_log is None."""
        from app.core.observability.logging import configure_logging

        import app.core.observability.logging as log_module

        log_module._installed_record_factory = False

        with patch.dict(os.environ, {"UVICORN_ACCESS_LOG": "true"}, clear=False):
            configure_logging(debug=False, service_name="test", access_log=None)
            # Just verify no exception

    def test_adds_file_handler_when_enabled(self) -> None:
        """Test adds file handler when LOG_TO_FILE is true."""
        from app.core.observability.logging import configure_logging

        import app.core.observability.logging as log_module

        log_module._installed_record_factory = False

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                os.environ,
                {"LOG_TO_FILE": "true", "LOG_DIR": tmpdir},
                clear=False,
            ):
                configure_logging(debug=False, service_name="test", access_log=False)

                root = logging.getLogger()
                # Should have 2 handlers: stdout + file
                assert len(root.handlers) == 2
                handler_types = [type(h).__name__ for h in root.handlers]
                assert "StreamHandler" in handler_types
                assert "TimedRotatingFileHandler" in handler_types


if __name__ == "__main__":
    unittest.main()
