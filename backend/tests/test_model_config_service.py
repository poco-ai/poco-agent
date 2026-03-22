import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.model_config_service import ModelConfigService


class ModelConfigServiceProviderTests(unittest.TestCase):
    @staticmethod
    def _make_settings() -> SimpleNamespace:
        return SimpleNamespace(
            default_model="claude-sonnet-4-6",
            model_list=[],
            mem0_enabled=False,
            secret_key="test-secret",
        )

    def test_model_config_includes_anthropic_auth_token_provider(self) -> None:
        settings = self._make_settings()

        with (
            patch("app.services.model_config_service.get_settings", return_value=settings),
            patch(
                "app.services.model_config_service.ModelProviderSettingRepository.list_by_user_id",
                return_value=[],
            ),
            patch(
                "app.services.model_config_service.EnvVarRepository.list_by_user_and_scope",
                return_value=[],
            ),
        ):
            service = ModelConfigService()
            config = service.get_model_config(object(), "user-123")

        provider = next(
            (
                item
                for item in config.providers
                if item.provider_id == "anthropic-authtoken"
            ),
            None,
        )

        self.assertIsNotNone(provider)
        self.assertEqual(provider.display_name, "Anthropic AuthToken")
        self.assertEqual(provider.api_key_env_key, "ANTHROPIC_AUTH_TOKEN")
        self.assertEqual(provider.default_base_url, "https://api.anthropic.com")


if __name__ == "__main__":
    unittest.main()
