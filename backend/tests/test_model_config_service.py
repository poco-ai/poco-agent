import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.model_config_service import (
    PROVIDER_SPEC_MAP,
    ProviderSpec,
    ModelConfigService,
    get_allowed_model_ids,
    humanize_model_name,
    infer_provider_id,
)


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
            patch(
                "app.services.model_config_service.get_settings", return_value=settings
            ),
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


class TestInferProviderId(unittest.TestCase):
    """Test infer_provider_id function."""

    def test_claude_models(self) -> None:
        self.assertEqual(infer_provider_id("claude-sonnet-4-6"), "anthropic")
        self.assertEqual(infer_provider_id("claude-opus-4-6"), "anthropic")

    def test_glm_models(self) -> None:
        self.assertEqual(infer_provider_id("glm-4.7"), "glm")
        self.assertEqual(infer_provider_id("GLM-4.7"), "glm")

    def test_minimax_models(self) -> None:
        self.assertEqual(infer_provider_id("minimax-m2.5"), "minimax")
        self.assertEqual(infer_provider_id("MiniMax-M2.5"), "minimax")

    def test_deepseek_models(self) -> None:
        self.assertEqual(infer_provider_id("deepseek-chat"), "deepseek")

    def test_unknown_model(self) -> None:
        self.assertIsNone(infer_provider_id("unknown-model"))

    def test_empty_model(self) -> None:
        self.assertIsNone(infer_provider_id(""))
        self.assertIsNone(infer_provider_id(None))


class TestHumanizeModelName(unittest.TestCase):
    """Test humanize_model_name function."""

    def test_known_model(self) -> None:
        self.assertEqual(humanize_model_name("claude-sonnet-4-6"), "Claude Sonnet 4.6")

    def test_unknown_model(self) -> None:
        result = humanize_model_name("my-custom-model")
        self.assertIn("my", result.lower())

    def test_empty_model(self) -> None:
        self.assertEqual(humanize_model_name(""), "")


class TestGetAllowedModelIds(unittest.TestCase):
    """Test get_allowed_model_ids function."""

    def test_default_settings(self) -> None:
        settings = SimpleNamespace(
            default_model="claude-sonnet-4-6",
            model_list=["glm-4.7", "deepseek-chat"],
        )

        result = get_allowed_model_ids(settings)

        self.assertIn("claude-sonnet-4-6", result)
        self.assertIn("glm-4.7", result)
        self.assertIn("deepseek-chat", result)

    def test_filters_unknown_providers(self) -> None:
        settings = SimpleNamespace(
            default_model="claude-sonnet-4-6",
            model_list=["gpt-4", "unknown-model"],
        )

        result = get_allowed_model_ids(settings)

        self.assertIn("claude-sonnet-4-6", result)
        self.assertNotIn("gpt-4", result)

    def test_deduplicates_models(self) -> None:
        settings = SimpleNamespace(
            default_model="claude-sonnet-4-6",
            model_list=["claude-sonnet-4-6"],
        )

        result = get_allowed_model_ids(settings)

        self.assertEqual(result.count("claude-sonnet-4-6"), 1)


class TestProviderSpecMap(unittest.TestCase):
    """Test PROVIDER_SPEC_MAP contains expected providers."""

    def test_has_anthropic_provider(self) -> None:
        self.assertIn("anthropic", PROVIDER_SPEC_MAP)
        spec = PROVIDER_SPEC_MAP["anthropic"]
        assert spec is not None
        self.assertEqual(spec.display_name, "Anthropic")

    def test_provider_spec_attributes(self) -> None:
        spec = PROVIDER_SPEC_MAP["anthropic"]
        assert spec is not None
        self.assertIsInstance(spec, ProviderSpec)
        self.assertEqual(spec.api_key_env_key, "ANTHROPIC_API_KEY")


if __name__ == "__main__":
    unittest.main()
