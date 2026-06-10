import unittest
from unittest.mock import MagicMock

from app.core.settings import Settings
from app.services.session_title_service import SessionTitleService


class SessionTitleServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionTitleService()
        settings = Settings()
        settings.default_model = "claude-sonnet-4-6"
        settings.model_list = []
        settings.anthropic_api_key = ""
        settings.anthropic_base_url = ""
        settings.glm_api_key = ""
        settings.glm_base_url = ""
        settings.minimax_api_key = ""
        settings.minimax_base_url = ""
        settings.deepseek_api_key = ""
        settings.deepseek_base_url = ""
        self.service.settings = settings
        self.service.env_var_service = MagicMock()

    def test_resolves_glm_provider_for_glm_default_model(self) -> None:
        self.service.env_var_service.get_system_env_map.return_value = {
            "DEFAULT_MODEL": "glm-4.7",
            "GLM_API_KEY": "glm-key",
        }

        config = self.service._resolve_model_config(MagicMock())

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.provider_id, "glm")
        self.assertEqual(config.model, "glm-4.7")
        self.assertEqual(config.api_key, "glm-key")
        self.assertEqual(config.base_url, "https://open.bigmodel.cn/api/anthropic")

    def test_resolves_glm_provider_from_settings_env_file_fields(self) -> None:
        self.service.settings.default_model = "glm-5-turbo"
        self.service.settings.glm_api_key = "glm-settings-key"
        self.service.settings.glm_base_url = "https://glm.example.test/anthropic"
        self.service.env_var_service.get_system_env_map.return_value = {}

        config = self.service._resolve_model_config(MagicMock())

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.provider_id, "glm")
        self.assertEqual(config.model, "glm-5-turbo")
        self.assertEqual(config.api_key, "glm-settings-key")
        self.assertEqual(config.base_url, "https://glm.example.test/anthropic")

    def test_falls_back_to_configured_provider_when_default_provider_has_no_key(
        self,
    ) -> None:
        self.service.env_var_service.get_system_env_map.return_value = {
            "GLM_API_KEY": "glm-key",
        }

        config = self.service._resolve_model_config(MagicMock())

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.provider_id, "glm")
        self.assertEqual(config.model, "glm-4.7")
        self.assertEqual(config.api_key, "glm-key")

    def test_disables_title_generation_without_provider_credentials(self) -> None:
        self.service.env_var_service.get_system_env_map.return_value = {}

        config = self.service._resolve_model_config(MagicMock())

        self.assertIsNone(config)


if __name__ == "__main__":
    unittest.main()
