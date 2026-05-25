import unittest
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


if __name__ == "__main__":
    unittest.main()
