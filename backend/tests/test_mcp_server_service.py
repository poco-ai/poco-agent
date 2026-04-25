from datetime import UTC, datetime
import unittest
from unittest.mock import MagicMock, patch

from app.models.mcp_server import McpServer
from app.services.mcp_server_service import McpServerService


class McpServerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = McpServerService()
        self.now = datetime.now(UTC)

    def _build_server(
        self,
        *,
        scope: str,
        owner_user_id: str = "user-1",
        server_config: dict | None = None,
    ) -> McpServer:
        return McpServer(
            id=1,
            name="MiniMax",
            description="Test MCP",
            scope=scope,
            owner_user_id=owner_user_id,
            server_config=server_config
            or {
                "mcpServers": {
                    "MiniMax": {
                        "command": "uvx",
                        "env": {
                            "MINIMAX_API_KEY": "sk-9e136e398575f4ffc42ff2f4ffc42ff2",
                            "MINIMAX_API_HOST": "https://api.example.com",
                        },
                    }
                }
            },
            default_enabled=False,
            force_enabled=False,
            created_at=self.now,
            updated_at=self.now,
        )

    def test_to_response_masks_system_server_config(self) -> None:
        server = self._build_server(scope="system", owner_user_id="__system__")

        response = self.service._to_response(server)

        self.assertTrue(response.has_sensitive_data)
        self.assertEqual(
            response.server_config["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_KEY"],
            "sk-9...2ff2",
        )
        self.assertEqual(
            response.server_config["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_HOST"],
            "https://api.example.com",
        )

    def test_to_response_keeps_user_server_config_unmasked(self) -> None:
        server = self._build_server(scope="user")

        response = self.service._to_response(server)

        self.assertFalse(response.has_sensitive_data)
        self.assertEqual(
            response.server_config["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_KEY"],
            "sk-9e136e398575f4ffc42ff2f4ffc42ff2",
        )

    def test_to_admin_response_includes_raw_and_masked_config(self) -> None:
        server = self._build_server(scope="system", owner_user_id="__system__")

        response = self.service._to_admin_response(server)

        self.assertTrue(response.has_sensitive_data)
        self.assertEqual(
            response.server_config["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_KEY"],
            "sk-9e136e398575f4ffc42ff2f4ffc42ff2",
        )
        self.assertEqual(
            response.masked_server_config["mcpServers"]["MiniMax"]["env"][
                "MINIMAX_API_KEY"
            ],
            "sk-9...2ff2",
        )

    def test_list_servers_for_admin_uses_admin_response_shape(self) -> None:
        db = MagicMock()
        server = self._build_server(scope="system", owner_user_id="__system__")

        with patch(
            "app.services.mcp_server_service.McpServerRepository.list_visible",
            return_value=[server],
        ) as list_visible:
            result = self.service.list_servers_for_admin(db, user_id="__system__")

        list_visible.assert_called_once_with(db, user_id="__system__")
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0].server_config["mcpServers"]["MiniMax"]["env"]["MINIMAX_API_KEY"],
            "sk-9e136e398575f4ffc42ff2f4ffc42ff2",
        )
        self.assertEqual(
            result[0].masked_server_config["mcpServers"]["MiniMax"]["env"][
                "MINIMAX_API_KEY"
            ],
            "sk-9...2ff2",
        )


if __name__ == "__main__":
    unittest.main()
