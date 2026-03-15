import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from app.core.settings import Settings
from app.services.container_pool import ContainerPool


class ExecutorManagerSettingsTests(unittest.TestCase):
    def test_accepts_api_key_only(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(anthropic_api_key="api-key")

        self.assertEqual(settings.anthropic_api_key, "api-key")

    def test_accepts_auth_token_only(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(anthropic_auth_token="auth-token")

        self.assertEqual(settings.anthropic_auth_token, "auth-token")

    def test_rejects_missing_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                Settings()


class ContainerEnvironmentTests(unittest.TestCase):
    @staticmethod
    def _make_settings() -> SimpleNamespace:
        return SimpleNamespace(
            anthropic_base_url="https://api.example.com",
            anthropic_api_key="api-key",
            anthropic_auth_token="auth-token",
            default_model="claude-sonnet-4-20250514",
            executor_memory_limit="2g",
            executor_browser_memory_limit="4g",
            executor_timezone="Asia/Shanghai",
            poco_browser_viewport_size="1366x768",
            playwright_mcp_output_mode="file",
            playwright_mcp_image_responses="omit",
        )

    def test_container_environment_includes_auth_token(self) -> None:
        environment = ContainerPool._build_container_environment(
            settings=self._make_settings(),
            session_id="session-123",
            user_id="user-456",
            browser_enabled=True,
        )

        self.assertEqual(environment["ANTHROPIC_AUTH_TOKEN"], "auth-token")
        self.assertEqual(environment["ANTHROPIC_API_KEY"], "api-key")
        self.assertEqual(environment["USER_ID"], "user-456")
        self.assertEqual(environment["SESSION_ID"], "session-123")
        self.assertEqual(environment["POCO_BROWSER_VIEWPORT_SIZE"], "1366x768")

    def test_browser_container_uses_browser_memory_limit(self) -> None:
        memory_limit = ContainerPool._resolve_container_memory_limit(
            settings=self._make_settings(),
            browser_enabled=True,
        )

        self.assertEqual(memory_limit, "4g")

    def test_regular_container_uses_default_memory_limit(self) -> None:
        memory_limit = ContainerPool._resolve_container_memory_limit(
            settings=self._make_settings(),
            browser_enabled=False,
        )

        self.assertEqual(memory_limit, "2g")


if __name__ == "__main__":
    unittest.main()
