"""Tests for model provider validation in TaskService."""

import unittest

from app.services.task_service import TaskService
from app.core.errors.exceptions import AppException


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


if __name__ == "__main__":
    unittest.main()
