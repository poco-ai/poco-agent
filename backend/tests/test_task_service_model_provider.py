"""Tests for model provider validation in TaskService."""

import unittest
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.services.task_service import TaskService


class TestTaskServiceModelProviderValidation(unittest.TestCase):
    """Test model/provider pair validation."""

    def test_allows_anthropic_authtoken_with_claude_models(self):
        """anthropic-authtoken should be allowed with claude-* model ids."""
        config = {
            "model": "claude-sonnet-4-6",
            "model_provider_id": "anthropic-authtoken",
        }
        # Should not raise - anthropic-authtoken is a valid provider for claude models
        TaskService._validate_and_normalize_model(config)
        self.assertEqual(config["model"], "claude-sonnet-4-6")
        self.assertEqual(config["model_provider_id"], "anthropic-authtoken")

    def test_allows_explicit_provider_for_custom_glm_model(self):
        """Explicit provider should win for custom models configured under that provider."""
        config = {
            "model": "glm-5",
            "model_provider_id": "anthropic-authtoken",
        }
        TaskService._validate_and_normalize_model(config)
        self.assertEqual(config["model"], "glm-5")
        self.assertEqual(config["model_provider_id"], "anthropic-authtoken")

    def test_allows_anthropic_provider_with_claude_models(self):
        """anthropic provider should work with claude models."""
        config = {
            "model": "claude-opus-4-6",
            "model_provider_id": "anthropic",
        }
        TaskService._validate_and_normalize_model(config)
        self.assertEqual(config["model"], "claude-opus-4-6")
        self.assertEqual(config["model_provider_id"], "anthropic")

    def test_rejects_unknown_provider(self):
        """Unknown providers should still be rejected."""
        config = {
            "model": "glm-5",
            "model_provider_id": "unknown-provider",
        }
        with self.assertRaises(AppException) as ctx:
            TaskService._validate_and_normalize_model(config)
        self.assertIn("Invalid model provider", str(ctx.exception.message))

    @patch("app.services.task_service.get_settings")
    def test_preserves_default_model_when_explicit_provider_changes_runtime(
        self, mock_settings: MagicMock
    ) -> None:
        """Default-model selections must keep explicit providers that change runtime."""
        mock_settings.return_value.default_model = "claude-sonnet-4-6"

        config = {
            "model": "claude-sonnet-4-6",
            "model_provider_id": "anthropic-authtoken",
        }

        TaskService._validate_and_normalize_model(config)

        self.assertEqual(config["model"], "claude-sonnet-4-6")
        self.assertEqual(config["model_provider_id"], "anthropic-authtoken")

    @patch("app.services.task_service.get_settings")
    def test_drops_default_model_when_provider_matches_default_runtime(
        self, mock_settings: MagicMock
    ) -> None:
        """Redundant provider bindings for the default runtime should be normalized away."""
        mock_settings.return_value.default_model = "claude-sonnet-4-6"

        config = {
            "model": "claude-sonnet-4-6",
            "model_provider_id": "anthropic",
        }

        TaskService._validate_and_normalize_model(config)

        self.assertNotIn("model", config)
        self.assertNotIn("model_provider_id", config)


if __name__ == "__main__":
    unittest.main()
