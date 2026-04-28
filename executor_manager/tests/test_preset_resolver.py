import unittest
from unittest.mock import AsyncMock, MagicMock

from app.services.config_resolver import ConfigResolver
from app.services.preset_service import PresetResolver


class PresetResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_preset_config_merges_manual_overrides_and_lists(self) -> None:
        backend_client = MagicMock()
        backend_client.get_preset = AsyncMock(
            return_value={
                "preset_id": 8,
                "prompt_template": "baseline",
                "browser_enabled": True,
                "memory_enabled": False,
                "skill_ids": [1, 2],
                "mcp_server_ids": [10],
                "plugin_ids": [20],
                "subagent_configs": [
                    {
                        "name": "reviewer",
                        "description": "Review code",
                        "prompt": "Review the patch",
                        "tools": ["Read"],
                    }
                ],
            }
        )
        resolver = PresetResolver(backend_client)

        merged = await resolver.apply_preset_config(
            user_id="user-1",
            config_snapshot={
                "preset_id": 8,
                "browser_enabled": False,
                "skill_ids": [2, 3],
                "local_mounts": [{"name": "workspace"}],
                "subagent_configs": [
                    {
                        "name": "reviewer",
                        "description": "Review deeply",
                        "prompt": "Review the patch thoroughly",
                        "tools": ["Read", "Bash"],
                    },
                    {
                        "name": "planner",
                        "description": "Plan",
                        "prompt": "Draft a plan",
                    },
                ],
            },
        )

        self.assertEqual(merged["preset_id"], 8)
        self.assertFalse(merged["browser_enabled"])
        self.assertEqual(merged["skill_ids"], [1, 2, 3])
        self.assertEqual(merged["mcp_server_ids"], [10])
        self.assertEqual(merged["plugin_ids"], [20])
        self.assertEqual(merged["local_mounts"], [{"name": "workspace"}])
        self.assertEqual(
            merged["subagent_configs"],
            [
                {
                    "name": "reviewer",
                    "description": "Review deeply",
                    "prompt": "Review the patch thoroughly",
                    "model": None,
                    "tools": ["Read", "Bash"],
                },
                {
                    "name": "planner",
                    "description": "Plan",
                    "prompt": "Draft a plan",
                    "model": None,
                    "tools": None,
                },
            ],
        )


class ConfigResolverTests(unittest.TestCase):
    def test_resolve_inline_subagent_configs_filters_invalid_entries(self) -> None:
        resolved = ConfigResolver._resolve_inline_subagent_configs(
            [
                {
                    "name": "reviewer",
                    "description": "Review code",
                    "prompt": "Review the patch",
                    "tools": ["Read", " ", "Bash"],
                    "model": "sonnet",
                },
                {
                    "name": "missing-description",
                    "description": "",
                    "prompt": "Ignored",
                },
                {
                    "name": "missing-prompt",
                    "description": "Ignored",
                    "prompt": "",
                },
            ]
        )

        self.assertEqual(
            resolved,
            {
                "reviewer": {
                    "description": "Review code",
                    "prompt": "Review the patch",
                    "tools": ["Read", "Bash"],
                    "model": "sonnet",
                }
            },
        )

    def test_resolve_model_env_overrides_uses_system_default_model(self) -> None:
        resolver = ConfigResolver(backend_client=MagicMock())

        overrides = resolver._resolve_model_env_overrides(
            {},
            {
                "DEFAULT_MODEL": "minimax-default",
                "MINIMAX_API_KEY": "minimax-key",
                "MINIMAX_BASE_URL": "https://minimax.example.com/anthropic",
            },
            user_id="user-1",
        )

        self.assertEqual(overrides["DEFAULT_MODEL"], "minimax-default")
        self.assertEqual(overrides["ANTHROPIC_API_KEY"], "minimax-key")
        self.assertEqual(
            overrides["ANTHROPIC_BASE_URL"],
            "https://minimax.example.com/anthropic",
        )


if __name__ == "__main__":
    unittest.main()
