import unittest
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import (
    agent_channel_artifacts,
    agent_channel_runtime,
    agent_channel_tasks,
    callback,
    computer,
    memories,
    user_input_requests,
)
from app.schemas.callback import CallbackReceiveResponse, CallbackStatus
from app.schemas.computer import ComputerScreenshotUploadResponse


CALLBACK_TOKEN = "callback-token"


class ExecutorManagerProxyAuthTests(unittest.TestCase):
    def _app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(callback.router, prefix="/api/v1")
        app.include_router(computer.router, prefix="/api/v1")
        app.include_router(memories.router, prefix="/api/v1")
        app.include_router(agent_channel_runtime.router, prefix="/api/v1")
        app.include_router(agent_channel_artifacts.router, prefix="/api/v1")
        app.include_router(agent_channel_tasks.router, prefix="/api/v1")
        app.include_router(user_input_requests.router, prefix="/api/v1")
        return app

    def _settings(self) -> MagicMock:
        return MagicMock(callback_token=CALLBACK_TOKEN)

    def _user_input_payload(self) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": "request-1",
            "session_id": "session-1",
            "tool_name": "ask_user",
            "tool_input": {},
            "status": "pending",
            "answers": None,
            "expires_at": now,
            "answered_at": None,
            "created_at": now,
            "updated_at": now,
        }

    @contextmanager
    def _with_common_patches(self) -> Iterator[None]:
        callback_response = CallbackReceiveResponse(
            status="received",
            session_id="session-1",
            callback_status=CallbackStatus.RUNNING,
            progress=10,
        )
        screenshot_response = ComputerScreenshotUploadResponse(
            session_id="session-1",
            run_id=None,
            tool_use_id="tool-1",
            key="screenshots/session-1/tool-1.png",
            content_type="image/png",
            size_bytes=4,
        )
        patchers = [
            patch("app.core.deps.get_settings", return_value=self._settings()),
            patch(
                "app.api.v1.callback.callback_service.process_callback",
                new=AsyncMock(return_value=callback_response),
            ),
            patch(
                "app.api.v1.computer.computer_service.upload_browser_screenshot",
                return_value=screenshot_response,
            ),
            patch(
                "app.api.v1.memories.backend_client.create_memory",
                new=AsyncMock(return_value={"job_id": "job-1", "status": "queued"}),
            ),
            patch(
                "app.api.v1.agent_channel_runtime."
                "backend_client.read_agent_channel_messages",
                new=AsyncMock(return_value={"messages": []}),
            ),
            patch(
                "app.api.v1.agent_channel_artifacts."
                "backend_client.list_agent_channel_artifacts",
                new=AsyncMock(return_value={"artifacts": []}),
            ),
            patch(
                "app.api.v1.agent_channel_tasks.backend_client.list_agent_channel_tasks",
                new=AsyncMock(return_value={"tasks": []}),
            ),
            patch(
                "app.api.v1.user_input_requests."
                "backend_client.create_user_input_request",
                new=AsyncMock(return_value=self._user_input_payload()),
            ),
        ]
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            yield

    def test_proxy_routes_reject_missing_callback_token(self) -> None:
        client = TestClient(self._app())
        requests = [
            (
                "POST",
                "/api/v1/callback",
                {
                    "session_id": "session-1",
                    "status": "running",
                    "progress": 10,
                },
                None,
            ),
            (
                "POST",
                "/api/v1/memories",
                {
                    "session_id": "session-1",
                    "messages": [{"role": "user", "content": "remember this"}],
                },
                None,
            ),
            (
                "POST",
                "/api/v1/agent-channel-runtime/messages/read",
                {"session_id": "session-1"},
                None,
            ),
            (
                "POST",
                "/api/v1/agent-channel-artifacts/list",
                {"session_id": "session-1"},
                None,
            ),
            (
                "POST",
                "/api/v1/agent-channel-tasks/list",
                {"session_id": "session-1"},
                None,
            ),
            (
                "POST",
                "/api/v1/user-input-requests",
                {
                    "session_id": "session-1",
                    "tool_name": "ask_user",
                    "tool_input": {},
                },
                None,
            ),
        ]

        with self._with_common_patches():
            for method, path, body, mode in requests:
                with self.subTest(path=path):
                    response = client.request(method, path, json=body)
                    self.assertEqual(response.status_code, 403)
            with self.subTest(path="/api/v1/computer/screenshots"):
                response = client.request(
                    "POST",
                    "/api/v1/computer/screenshots",
                    data={
                        "session_id": "session-1",
                        "tool_use_id": "tool-1",
                    },
                    files={"file": ("screenshot.png", b"data", "image/png")},
                )
                self.assertEqual(response.status_code, 403)

    def test_proxy_routes_reject_internal_token_as_callback_token(self) -> None:
        client = TestClient(self._app())

        with self._with_common_patches():
            response = client.post(
                "/api/v1/callback",
                json={
                    "session_id": "session-1",
                    "status": "running",
                    "progress": 10,
                },
                headers={"Authorization": "Bearer internal-token"},
            )

        self.assertEqual(response.status_code, 403)

    def test_proxy_routes_accept_valid_callback_token(self) -> None:
        client = TestClient(self._app())
        headers = {"Authorization": f"Bearer {CALLBACK_TOKEN}"}

        with self._with_common_patches():
            callback_response = client.post(
                "/api/v1/callback",
                json={
                    "session_id": "session-1",
                    "status": "running",
                    "progress": 10,
                },
                headers=headers,
            )
            memory_response = client.post(
                "/api/v1/memories",
                json={
                    "session_id": "session-1",
                    "messages": [{"role": "user", "content": "remember this"}],
                },
                headers=headers,
            )
            channel_response = client.post(
                "/api/v1/agent-channel-runtime/messages/read",
                json={"session_id": "session-1"},
                headers=headers,
            )

        self.assertEqual(callback_response.status_code, 200)
        self.assertEqual(memory_response.status_code, 200)
        self.assertEqual(channel_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
