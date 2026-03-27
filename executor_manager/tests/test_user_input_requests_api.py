"""Tests for app/api/v1/user_input_requests.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestUserInputRequestsEndpoints(unittest.TestCase):
    """Test /api/v1/user-input-requests endpoints."""

    def test_create_user_input_request_success(self) -> None:
        """Test successful user input request creation."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.create_user_input_request = AsyncMock(
            return_value={"id": "req-123", "status": "pending"}
        )

        with patch(
            "app.api.v1.user_input_requests.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/user-input-requests",
                json={
                    "session_id": "session-123",
                    "tool_name": "ask_user",
                    "tool_input": {"question": "What is the capital of France?"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["id"] == "req-123"
            mock_client.create_user_input_request.assert_called_once()

    def test_create_user_input_request_with_expires_at(self) -> None:
        """Test user input request creation with expires_at."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.create_user_input_request = AsyncMock(
            return_value={"id": "req-456", "status": "pending"}
        )

        with patch(
            "app.api.v1.user_input_requests.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/user-input-requests",
                json={
                    "session_id": "session-456",
                    "tool_name": "ask_user",
                    "tool_input": {"question": "Test prompt"},
                    "expires_at": "2026-04-01T00:00:00Z",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["id"] == "req-456"

    def test_get_user_input_request_success(self) -> None:
        """Test successful user input request retrieval."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.get_user_input_request = AsyncMock(
            return_value={
                "request_id": "req-123",
                "status": "completed",
                "response": "Paris",
            }
        )

        with patch(
            "app.api.v1.user_input_requests.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/user-input-requests/req-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["request_id"] == "req-123"
            mock_client.get_user_input_request.assert_called_once_with("req-123")

    def test_get_user_input_request_not_found(self) -> None:
        """Test user input request not found."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.get_user_input_request = AsyncMock(return_value=None)

        with patch(
            "app.api.v1.user_input_requests.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/user-input-requests/nonexistent")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0


if __name__ == "__main__":
    unittest.main()
