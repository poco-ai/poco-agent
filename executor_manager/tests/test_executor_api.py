"""Tests for app/api/v1/executor.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestExecutorEndpoints(unittest.TestCase):
    """Test /api/v1/executor endpoints."""

    def test_cancel_task_success(self) -> None:
        """Test successful task cancellation."""
        from app.main import app

        mock_pool = MagicMock()
        mock_pool.cancel_task = AsyncMock()

        with patch(
            "app.api.v1.executor.TaskDispatcher.get_container_pool",
            return_value=mock_pool,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/executor/cancel",
                json={"session_id": "session-123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["session_id"] == "session-123"
            assert data["data"]["status"] == "canceled"
            mock_pool.cancel_task.assert_called_once_with("session-123")

    def test_delete_container_success(self) -> None:
        """Test successful container deletion."""
        from app.main import app

        mock_pool = MagicMock()
        mock_pool.delete_container = AsyncMock()

        with patch(
            "app.api.v1.executor.TaskDispatcher.get_container_pool",
            return_value=mock_pool,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/executor/delete",
                json={"container_id": "container-456"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["container_id"] == "container-456"
            assert data["data"]["status"] == "deleted"
            mock_pool.delete_container.assert_called_once_with("container-456")

    def test_get_executor_load_success(self) -> None:
        """Test successful load stats retrieval."""
        from app.main import app

        mock_pool = MagicMock()
        mock_pool.get_container_stats.return_value = {
            "total_containers": 5,
            "active_containers": 3,
            "idle_containers": 2,
        }

        with patch(
            "app.api.v1.executor.TaskDispatcher.get_container_pool",
            return_value=mock_pool,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/executor/load")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["total_containers"] == 5
            assert data["data"]["active_containers"] == 3
            mock_pool.get_container_stats.assert_called_once()

    def test_cancel_task_with_empty_session_id(self) -> None:
        """Test cancel task with empty session_id."""
        from app.main import app

        mock_pool = MagicMock()
        mock_pool.cancel_task = AsyncMock()

        with patch(
            "app.api.v1.executor.TaskDispatcher.get_container_pool",
            return_value=mock_pool,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/executor/cancel",
                json={"session_id": ""},
            )

            # Should still work (validation is on the model)
            # The endpoint calls cancel_task with empty string
            assert response.status_code == 200

    def test_get_executor_load_empty_stats(self) -> None:
        """Test load stats when no containers."""
        from app.main import app

        mock_pool = MagicMock()
        mock_pool.get_container_stats.return_value = {}

        with patch(
            "app.api.v1.executor.TaskDispatcher.get_container_pool",
            return_value=mock_pool,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/executor/load")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"] == {}


if __name__ == "__main__":
    unittest.main()
