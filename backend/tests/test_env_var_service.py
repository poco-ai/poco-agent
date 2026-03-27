import unittest

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.env_var_service import (
    PROCESS_ENV_KEYS,
    SYSTEM_USER_ID,
    _normalize_key,
    _normalize_user_value,
    _require_regular_user_id,
    _require_scope,
)


class TestEnvVarHelpers(unittest.TestCase):
    """Test env_var_service helper functions."""

    def test_require_scope_valid(self) -> None:
        self.assertEqual(_require_scope("system"), "system")
        self.assertEqual(_require_scope("user"), "user")

    def test_require_scope_invalid(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _require_scope("invalid")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_normalize_key_valid(self) -> None:
        self.assertEqual(_normalize_key("API_KEY"), "API_KEY")
        self.assertEqual(_normalize_key("  API_KEY  "), "API_KEY")

    def test_normalize_key_empty(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _normalize_key("")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_normalize_key_whitespace(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _normalize_key("   ")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_normalize_user_value_valid(self) -> None:
        self.assertEqual(_normalize_user_value("secret123"), "secret123")
        self.assertEqual(_normalize_user_value("  secret123  "), "secret123")

    def test_normalize_user_value_empty(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _normalize_user_value("")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_require_regular_user_id_valid(self) -> None:
        # Should not raise
        _require_regular_user_id("user-123")
        _require_regular_user_id("regular-user")

    def test_require_regular_user_id_system(self) -> None:
        with self.assertRaises(AppException) as ctx:
            _require_regular_user_id(SYSTEM_USER_ID)

        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)


class TestProcessEnvKeys(unittest.TestCase):
    """Test PROCESS_ENV_KEYS constant."""

    def test_contains_expected_keys(self) -> None:
        self.assertIn("ANTHROPIC_API_KEY", PROCESS_ENV_KEYS)
        self.assertIn("OPENAI_API_KEY", PROCESS_ENV_KEYS)
        self.assertIn("GLM_API_KEY", PROCESS_ENV_KEYS)

    def test_is_tuple(self) -> None:
        self.assertIsInstance(PROCESS_ENV_KEYS, tuple)


if __name__ == "__main__":
    unittest.main()
