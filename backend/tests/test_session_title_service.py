import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.session_title_service import SessionTitleService


class SessionTitleServiceAuthTests(unittest.TestCase):
    @staticmethod
    def _make_settings(
        *,
        anthropic_api_key: str = "",
        anthropic_auth_token: str = "",
        anthropic_base_url: str = "https://api.anthropic.com",
        default_model: str = "claude-sonnet-4-20250514",
    ) -> SimpleNamespace:
        return SimpleNamespace(
            anthropic_api_key=anthropic_api_key,
            anthropic_auth_token=anthropic_auth_token,
            anthropic_base_url=anthropic_base_url,
            default_model=default_model,
        )

    def test_auth_token_takes_precedence_over_api_key(self) -> None:
        settings = self._make_settings(
            anthropic_api_key="api-key",
            anthropic_auth_token="auth-token",
            anthropic_base_url="https://example.com/v1",
        )

        with (
            patch("app.services.session_title_service.get_settings", return_value=settings),
            patch("app.services.session_title_service.Anthropic") as anthropic_cls,
        ):
            service = SessionTitleService()

        self.assertTrue(service._enabled)
        self.assertEqual(service._auth_mode, "token")
        self.assertEqual(service._messages_url, "https://example.com/v1/messages")
        self.assertEqual(
            service._build_messages_headers()["authorization"],
            "Bearer auth-token",
        )
        anthropic_cls.assert_not_called()

    def test_api_key_mode_uses_sdk_client(self) -> None:
        settings = self._make_settings(
            anthropic_api_key="api-key",
            anthropic_base_url="https://api.anthropic.com/v1",
        )

        with (
            patch("app.services.session_title_service.get_settings", return_value=settings),
            patch("app.services.session_title_service.Anthropic") as anthropic_cls,
        ):
            service = SessionTitleService()

        self.assertTrue(service._enabled)
        self.assertEqual(service._auth_mode, "api_key")
        anthropic_cls.assert_called_once_with(
            api_key="api-key",
            base_url="https://api.anthropic.com",
            timeout=15.0,
            max_retries=2,
        )

    def test_service_is_disabled_without_credentials(self) -> None:
        settings = self._make_settings()

        with (
            patch("app.services.session_title_service.get_settings", return_value=settings),
            patch("app.services.session_title_service.Anthropic") as anthropic_cls,
        ):
            service = SessionTitleService()

        self.assertFalse(service._enabled)
        self.assertIsNone(service._auth_mode)
        anthropic_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
