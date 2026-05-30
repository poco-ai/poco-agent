import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.agent_channel_artifacts import router


class AgentChannelArtifactsApiTests(unittest.TestCase):
    def test_read_artifact_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_artifacts."
            "backend_client.read_agent_channel_artifact",
            new=AsyncMock(return_value={"artifact": {"artifact_id": "artifact-1"}}),
        ) as read_artifact:
            response = TestClient(app).post(
                "/api/v1/agent-channel-artifacts/read",
                json={
                    "session_id": "session-1",
                    "artifact_id": "artifact-1",
                },
            )

        self.assertEqual(response.status_code, 200)
        read_artifact.assert_awaited_once_with(
            "session-1",
            {"artifact_id": "artifact-1"},
        )

    def test_read_artifact_preserves_backend_error_response(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        request = httpx.Request(
            "POST",
            "http://backend/api/v1/internal/channel-artifacts/read",
        )
        response = httpx.Response(
            404,
            json={
                "code": 40400,
                "message": "Channel artifact not found",
                "data": None,
            },
            request=request,
        )
        error = httpx.HTTPStatusError(
            "not found",
            request=request,
            response=response,
        )

        with patch(
            "app.api.v1.agent_channel_artifacts."
            "backend_client.read_agent_channel_artifact",
            new=AsyncMock(side_effect=error),
        ):
            result = TestClient(app).post(
                "/api/v1/agent-channel-artifacts/read",
                json={
                    "session_id": "session-1",
                    "logical_path": "Harness 工程核心指南.md",
                },
            )

        self.assertEqual(result.status_code, 404)
        body = result.json()
        self.assertEqual(body["code"], 40400)
        self.assertEqual(body["message"], "Channel artifact not found")

    def test_read_artifact_text_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_artifacts."
            "backend_client.read_agent_channel_artifact_text",
            new=AsyncMock(return_value={"content": "Experienced engineer"}),
        ) as read_text:
            response = TestClient(app).post(
                "/api/v1/agent-channel-artifacts/text",
                json={
                    "session_id": "session-1",
                    "artifact_id": "artifact-1",
                    "max_chars": 2000,
                },
            )

        self.assertEqual(response.status_code, 200)
        read_text.assert_awaited_once_with(
            "session-1",
            {"artifact_id": "artifact-1", "max_chars": 2000},
        )

    def test_download_artifact_preserves_binary_response(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_artifacts."
            "backend_client.download_agent_channel_artifact",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    content=b"%PDF-1.7",
                    media_type="application/pdf",
                    headers={"X-Artifact-Display-Name": "resume.pdf"},
                )
            ),
        ) as download_artifact:
            response = TestClient(app).post(
                "/api/v1/agent-channel-artifacts/download",
                json={
                    "session_id": "session-1",
                    "artifact_id": "artifact-1",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.7")
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.headers["x-artifact-display-name"], "resume.pdf")
        download_artifact.assert_awaited_once_with(
            "session-1",
            {"artifact_id": "artifact-1"},
        )


if __name__ == "__main__":
    unittest.main()
