import unittest

from app.services.admin_masking import mask_sensitive_structure


class AdminMaskingTests(unittest.TestCase):
    def test_masks_camel_case_secret_keys(self) -> None:
        masked, has_sensitive = mask_sensitive_structure(
            {"clientSecret": "abcdef1234567890"}
        )

        self.assertTrue(has_sensitive)
        self.assertEqual(masked["clientSecret"], "abcd...7890")

    def test_masks_kebab_case_api_key(self) -> None:
        masked, has_sensitive = mask_sensitive_structure(
            {"x-api-key": "sk-1234567890abcdef"}
        )

        self.assertTrue(has_sensitive)
        self.assertEqual(masked["x-api-key"], "sk-1...cdef")

    def test_masks_nested_minimax_api_key(self) -> None:
        masked, has_sensitive = mask_sensitive_structure(
            {
                "mcpServers": {
                    "MiniMax": {
                        "env": {
                            "MINIMAX_API_KEY": "sk-9e136e398575f4ffc42ff2f4ffc42ff2",
                            "MINIMAX_API_HOST": "https://api.example.com",
                        }
                    }
                }
            }
        )

        self.assertTrue(has_sensitive)
        self.assertEqual(
            masked["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_KEY"],
            "sk-9...2ff2",
        )
        self.assertEqual(
            masked["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_HOST"],
            "https://api.example.com",
        )

    def test_masks_database_url(self) -> None:
        masked, has_sensitive = mask_sensitive_structure(
            {"database_url": "postgresql://user:password@db.example.com:5432/app"}
        )

        self.assertTrue(has_sensitive)
        self.assertEqual(masked["database_url"], "post.../app")

    def test_does_not_mask_non_sensitive_fields(self) -> None:
        masked, has_sensitive = mask_sensitive_structure(
            {
                "base_url": "https://example.com",
                "command": "uvx",
                "args": ["minimax-coding-plan-mcp", "-y"],
            }
        )

        self.assertFalse(has_sensitive)
        self.assertEqual(
            masked,
            {
                "base_url": "https://example.com",
                "command": "uvx",
                "args": ["minimax-coding-plan-mcp", "-y"],
            },
        )


if __name__ == "__main__":
    unittest.main()
