import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.core.channel_runtime import (
    CHANNEL_RUNTIME_MCP_SERVER_KEY,
    ChannelRuntimeClient,
    _format_tool_error,
    _format_tool_result,
    _run_tool,
)


class ChannelRuntimeToolContractTests(unittest.IsolatedAsyncioTestCase):
    def _tool_text(self, result: dict) -> str:
        return result["content"][0]["text"]

    def test_unified_runtime_key_is_stable(self) -> None:
        self.assertEqual(CHANNEL_RUNTIME_MCP_SERVER_KEY, "__poco_channel_runtime")

    def test_format_tool_result_uses_title_and_json_body(self) -> None:
        result = _format_tool_result("read_channel_messages", {"messages": []})

        text = self._tool_text(result)
        self.assertTrue(text.startswith("read_channel_messages\n"))
        self.assertIn('"messages": []', text)

    def test_format_tool_error_includes_error_and_code(self) -> None:
        result = _format_tool_error(
            "read_channel_messages",
            "message_id must be provided",
            code="invalid_arguments",
        )

        text = self._tool_text(result)
        self.assertTrue(text.startswith("read_channel_messages_error\n"))
        self.assertIn('"error": "message_id must be provided"', text)
        self.assertIn('"code": "invalid_arguments"', text)

    async def test_run_tool_converts_exceptions_to_structured_error(self) -> None:
        async def fail() -> None:
            raise RuntimeError("backend unavailable")

        result = await _run_tool("list_channel_agents", fail())

        text = self._tool_text(result)
        self.assertTrue(text.startswith("list_channel_agents_error\n"))
        self.assertIn('"error": "backend unavailable"', text)
        self.assertIn('"code": "runtime_error"', text)

    async def test_client_uses_backend_error_message_for_failed_response(
        self,
    ) -> None:
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                pass

            async def post(self, *args, **kwargs) -> httpx.Response:
                request = httpx.Request(
                    "POST",
                    "http://manager/api/v1/agent-channel-artifacts/read",
                )
                return httpx.Response(
                    404,
                    json={
                        "code": 40400,
                        "message": "Channel artifact not found",
                        "data": None,
                    },
                    request=request,
                )

        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch("app.core.channel_runtime.httpx.AsyncClient", FakeAsyncClient):
            with self.assertRaises(RuntimeError) as ctx:
                await client.read_artifact(
                    artifact_id=None,
                    logical_path="Harness 工程核心指南.md",
                    max_bytes=None,
                )

        self.assertEqual(str(ctx.exception), "Channel artifact not found")

    async def test_client_reads_channel_messages_through_runtime_proxy(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"messages": []}),
        ) as request:
            result = await client.read_messages(
                message_ids=["message-1"],
                thread_root_message_id=None,
                anchor_message_id="anchor-1",
                direction="after",
                include_anchor=False,
                read_all=True,
                limit=20,
            )

        self.assertEqual(result, {"messages": []})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-runtime/messages/read",
            {
                "message_ids": ["message-1"],
                "thread_root_message_id": None,
                "anchor_message_id": "anchor-1",
                "direction": "after",
                "include_anchor": False,
                "read_all": True,
                "limit": 20,
            },
        )

    async def test_client_lists_channel_agents_through_runtime_proxy(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"agents": []}),
        ) as request:
            result = await client.list_agents()

        self.assertEqual(result, {"agents": []})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-runtime/agents/list",
            {},
        )

    async def test_client_requests_collaboration_through_runtime_proxy(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"status": "queued"}),
        ) as request:
            result = await client.request_collaboration(
                agent_handle="api",
                request_text="Please review this.",
                reason=None,
                mode="consult",
                thread_root_message_id=None,
                reference_message_ids=["message-1"],
                reference_artifact_ids=[],
            )

        self.assertEqual(result, {"status": "queued"})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-runtime/collaboration/request",
            {
                "agent_handle": "api",
                "request_text": "Please review this.",
                "reason": None,
                "mode": "consult",
                "thread_root_message_id": None,
                "reference_message_ids": ["message-1"],
                "reference_artifact_ids": [],
            },
        )

    async def test_client_routes_artifact_tools_through_facade(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"artifacts": []}),
        ) as request:
            result = await client.list_artifacts()

        self.assertEqual(result, {"artifacts": []})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-artifacts/list",
            {},
        )

    async def test_client_routes_task_tools_through_facade(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"task": {"title": "Review"}}),
        ) as request:
            result = await client.create_task(
                title="Review",
                description=None,
                priority="medium",
            )

        self.assertEqual(result, {"task": {"title": "Review"}})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-tasks/create",
            {"title": "Review", "description": None, "priority": "medium"},
        )

    async def test_client_lists_channel_tasks_through_facade(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"tasks": []}),
        ) as request:
            result = await client.list_tasks(status="todo", limit=20)

        self.assertEqual(result, {"tasks": []})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-tasks/list",
            {"status": "todo", "limit": 20},
        )

    async def test_client_reads_channel_task_through_facade(self) -> None:
        client = ChannelRuntimeClient("http://manager", "session-1")

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"task": {"title": "Review"}}),
        ) as request:
            result = await client.read_task(task_id="task-1")

        self.assertEqual(result, {"task": {"title": "Review"}})
        request.assert_awaited_once_with(
            "/api/v1/agent-channel-tasks/read",
            {"task_id": "task-1"},
        )


if __name__ == "__main__":
    unittest.main()
