import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.agent_channel_runtime import router


CALLBACK_TOKEN = "callback-token"
CALLBACK_HEADERS = {"Authorization": f"Bearer {CALLBACK_TOKEN}"}


class AgentChannelRuntimeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._settings_patch = patch(
            "app.core.deps.get_settings",
            return_value=MagicMock(callback_token=CALLBACK_TOKEN),
        )
        self._settings_patch.start()
        self.addCleanup(self._settings_patch.stop)

    def test_read_messages_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_runtime.backend_client.read_agent_channel_messages",
            new=AsyncMock(return_value={"messages": []}),
        ) as read_messages:
            response = TestClient(app).post(
                "/api/v1/agent-channel-runtime/messages/read",
                json={
                    "session_id": "session-1",
                    "message_ids": ["message-1"],
                },
                headers=CALLBACK_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        read_messages.assert_awaited_once_with(
            "session-1",
            {"message_ids": ["message-1"]},
        )

    def test_list_agents_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_runtime.backend_client.list_agent_channel_agents",
            new=AsyncMock(return_value={"agents": []}),
        ) as list_agents:
            response = TestClient(app).post(
                "/api/v1/agent-channel-runtime/agents/list",
                json={"session_id": "session-1"},
                headers=CALLBACK_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        list_agents.assert_awaited_once_with("session-1")

    def test_request_collaboration_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_runtime.backend_client.request_agent_channel_collaboration",
            new=AsyncMock(return_value={"status": "queued"}),
        ) as request_collaboration:
            response = TestClient(app).post(
                "/api/v1/agent-channel-runtime/collaboration/request",
                json={
                    "session_id": "session-1",
                    "agent_handle": "api",
                    "request_text": "Please review this.",
                },
                headers=CALLBACK_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        request_collaboration.assert_awaited_once_with(
            "session-1",
            {
                "agent_handle": "api",
                "request_text": "Please review this.",
            },
        )

    def test_add_reaction_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_runtime.backend_client.add_agent_channel_message_reaction",
            new=AsyncMock(return_value={"action": "add_channel_message_reaction"}),
        ) as add_reaction:
            response = TestClient(app).post(
                "/api/v1/agent-channel-runtime/reactions/add",
                json={
                    "session_id": "session-1",
                    "message_id": "message-1",
                    "emoji": "👍",
                },
                headers=CALLBACK_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        add_reaction.assert_awaited_once_with(
            "session-1",
            {"message_id": "message-1", "emoji": "👍"},
        )

    def test_remove_reaction_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_runtime.backend_client.remove_agent_channel_message_reaction",
            new=AsyncMock(return_value={"action": "remove_channel_message_reaction"}),
        ) as remove_reaction:
            response = TestClient(app).post(
                "/api/v1/agent-channel-runtime/reactions/remove",
                json={
                    "session_id": "session-1",
                    "message_id": "message-1",
                    "emoji": "✅",
                },
                headers=CALLBACK_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        remove_reaction.assert_awaited_once_with(
            "session-1",
            {"message_id": "message-1", "emoji": "✅"},
        )


if __name__ == "__main__":
    unittest.main()
