import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.core.callback import CallbackClient
from app.core.channel_runtime import ChannelRuntimeClient
from app.core.memory import MemoryClient
from app.core.user_input import UserInputClient
from app.schemas.callback import AgentCallbackRequest, CallbackStatus


CALLBACK_TOKEN = "callback-token"


class FakeAsyncClient:
    requests: list[dict]

    def __init__(self, *args, **kwargs) -> None:
        self.__class__.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    async def post(self, url: str, **kwargs) -> httpx.Response:
        self.__class__.requests.append({"method": "POST", "url": url, **kwargs})
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"code": 0, "data": {}}, request=request)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        self.__class__.requests.append({"method": "GET", "url": url, **kwargs})
        request = httpx.Request("GET", url)
        return httpx.Response(200, json={"code": 0, "data": {}}, request=request)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        self.__class__.requests.append({"method": method, "url": url, **kwargs})
        request = httpx.Request(method, url)
        return httpx.Response(200, json={"code": 0, "data": {}}, request=request)


class ManagerAuthClientTests(unittest.IsolatedAsyncioTestCase):
    def assertBearerHeader(self, request: dict) -> None:
        self.assertEqual(
            request["headers"]["Authorization"],
            f"Bearer {CALLBACK_TOKEN}",
        )

    async def test_callback_client_sends_callback_token(self) -> None:
        client = CallbackClient(
            callback_url="http://manager/api/v1/callback",
            callback_token=CALLBACK_TOKEN,
        )

        with patch("app.core.callback.httpx.AsyncClient", FakeAsyncClient):
            sent = await client.send(
                AgentCallbackRequest(
                    session_id="session-1",
                    status=CallbackStatus.RUNNING,
                    progress=10,
                )
            )

        self.assertTrue(sent)
        self.assertBearerHeader(FakeAsyncClient.requests[0])

    async def test_memory_client_sends_callback_token(self) -> None:
        client = MemoryClient(
            base_url="http://manager",
            session_id="session-1",
            callback_token=CALLBACK_TOKEN,
        )

        with patch("app.core.memory.httpx.AsyncClient", FakeAsyncClient):
            await client.list_memories()

        self.assertBearerHeader(FakeAsyncClient.requests[0])

    async def test_channel_runtime_client_sends_callback_token(self) -> None:
        client = ChannelRuntimeClient(
            base_url="http://manager",
            session_id="session-1",
            callback_token=CALLBACK_TOKEN,
        )

        with patch("app.core.channel_runtime.httpx.AsyncClient", FakeAsyncClient):
            await client.list_agents()

        self.assertBearerHeader(FakeAsyncClient.requests[0])

    async def test_user_input_client_sends_callback_token(self) -> None:
        client = UserInputClient(
            base_url="http://manager",
            callback_token=CALLBACK_TOKEN,
        )

        with patch("app.core.user_input.httpx.AsyncClient", FakeAsyncClient):
            await client.get_request("request-1")

        self.assertBearerHeader(FakeAsyncClient.requests[0])

    async def test_computer_client_sends_callback_token(self) -> None:
        from app.core.computer import ComputerClient

        client = ComputerClient(
            base_url="http://manager",
            callback_token=CALLBACK_TOKEN,
        )

        with patch("app.core.computer.httpx.AsyncClient", FakeAsyncClient):
            await client.upload_browser_screenshot(
                session_id="session-1",
                run_id=None,
                tool_use_id="tool-1",
                png_bytes=b"data",
            )

        self.assertBearerHeader(FakeAsyncClient.requests[0])


class RunTaskClientWiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_task_passes_callback_token_to_manager_clients(self) -> None:
        from app.api.v1.task import run_task
        from app.schemas.request import TaskConfig, TaskRun

        background_tasks = MagicMock()
        created_clients: dict[str, object] = {}

        def callback_factory(**kwargs):
            created_clients["callback"] = kwargs
            return AsyncMock()

        def user_input_factory(**kwargs):
            created_clients["user_input"] = kwargs
            return AsyncMock()

        def computer_factory(**kwargs):
            created_clients["computer"] = kwargs
            return AsyncMock()

        def memory_factory(**kwargs):
            created_clients["memory"] = kwargs
            return AsyncMock()

        with (
            patch("app.api.v1.task.CallbackClient", side_effect=callback_factory),
            patch("app.api.v1.task.UserInputClient", side_effect=user_input_factory),
            patch("app.api.v1.task.ComputerClient", side_effect=computer_factory),
            patch("app.api.v1.task.MemoryClient", side_effect=memory_factory),
            patch("app.api.v1.task.AgentExecutor"),
            patch("app.api.v1.task.CallbackHook"),
            patch("app.api.v1.task.BrowserScreenshotHook"),
        ):
            result = await run_task(
                TaskRun(
                    session_id="session-1",
                    prompt="hello",
                    callback_url="http://manager/api/v1/callback",
                    callback_base_url="http://manager",
                    callback_token=CALLBACK_TOKEN,
                    config=TaskConfig(memory_enabled=True, browser_enabled=True),
                ),
                background_tasks,
            )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(created_clients["callback"]["callback_token"], CALLBACK_TOKEN)
        self.assertEqual(created_clients["user_input"]["callback_token"], CALLBACK_TOKEN)
        self.assertEqual(created_clients["computer"]["callback_token"], CALLBACK_TOKEN)
        self.assertEqual(created_clients["memory"]["callback_token"], CALLBACK_TOKEN)


if __name__ == "__main__":
    unittest.main()
