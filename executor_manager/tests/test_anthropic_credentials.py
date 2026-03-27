import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from app.core.settings import Settings
from app.services.config_resolver import ConfigResolver
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
            callback_base_url="http://localhost:8001",
            callback_token="callback-token",
            default_model="claude-sonnet-4-20250514",
            executor_memory_limit="2g",
            executor_browser_memory_limit="4g",
            executor_timezone="Asia/Shanghai",
            poco_browser_viewport_size="1366x768",
            playwright_mcp_output_mode="file",
            playwright_mcp_image_responses="omit",
        )

    def test_container_environment_includes_runtime_context(self) -> None:
        environment = ContainerPool._build_container_environment(
            settings=self._make_settings(),
            session_id="session-123",
            user_id="user-456",
            browser_enabled=True,
        )

        self.assertEqual(environment["USER_ID"], "user-456")
        self.assertEqual(environment["SESSION_ID"], "session-123")
        self.assertEqual(environment["POCO_BROWSER_VIEWPORT_SIZE"], "1366x768")

    def test_container_environment_excludes_provider_credentials(self) -> None:
        environment = ContainerPool._build_container_environment(
            settings=self._make_settings(),
            session_id="session-123",
            user_id="user-456",
            browser_enabled=False,
        )

        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", environment)
        self.assertNotIn("ANTHROPIC_API_KEY", environment)

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


class ConfigResolverProviderOverrideTests(unittest.TestCase):
    @staticmethod
    def _make_settings() -> SimpleNamespace:
        return SimpleNamespace(
            anthropic_api_key="api-key",
            anthropic_auth_token="auth-token",
            anthropic_base_url="https://api.anthropic.com",
            glm_api_key="",
            glm_base_url="",
            minimax_api_key="",
            minimax_base_url="",
            deepseek_api_key="",
            deepseek_base_url="",
            default_model="claude-sonnet-4-6",
        )

    def test_auth_token_provider_uses_auth_token_runtime_env(self) -> None:
        resolver = object.__new__(ConfigResolver)
        resolver.settings = self._make_settings()

        overrides = resolver._resolve_model_env_overrides(
            {
                "model": "claude-sonnet-4-6",
                "model_provider_id": "anthropic-authtoken",
            },
            {"ANTHROPIC_AUTH_TOKEN": "runtime-auth-token"},
            user_id="user-123",
        )

        self.assertEqual(
            overrides["ANTHROPIC_AUTH_TOKEN"],
            "runtime-auth-token",
        )
        self.assertEqual(
            overrides["ANTHROPIC_BASE_URL"],
            "https://api.anthropic.com",
        )
        self.assertNotIn("ANTHROPIC_API_KEY", overrides)

    def test_auth_token_provider_injects_custom_model_aliases(self) -> None:
        resolver = object.__new__(ConfigResolver)
        resolver.settings = self._make_settings()

        overrides = resolver._resolve_model_env_overrides(
            {
                "model": "glm-5",
                "model_provider_id": "anthropic-authtoken",
            },
            {"ANTHROPIC_AUTH_TOKEN": "runtime-auth-token"},
            user_id="user-123",
        )

        self.assertEqual(overrides["ANTHROPIC_MODEL"], "glm-5")
        self.assertEqual(overrides["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "glm-5")
        self.assertEqual(overrides["ANTHROPIC_DEFAULT_SONNET_MODEL"], "glm-5")
        self.assertEqual(overrides["ANTHROPIC_DEFAULT_OPUS_MODEL"], "glm-5")

    def test_auth_token_provider_falls_back_to_anthropic_base_url(self) -> None:
        resolver = object.__new__(ConfigResolver)
        resolver.settings = SimpleNamespace(
            **{
                **self._make_settings().__dict__,
                "anthropic_base_url": "http://gateway.example.com",
            }
        )

        overrides = resolver._resolve_model_env_overrides(
            {
                "model": "glm-5",
                "model_provider_id": "anthropic-authtoken",
            },
            {"ANTHROPIC_AUTH_TOKEN": "runtime-auth-token"},
            user_id="user-123",
        )

        self.assertEqual(
            overrides["ANTHROPIC_BASE_URL"],
            "http://gateway.example.com",
        )


if __name__ == "__main__":
    unittest.main()
