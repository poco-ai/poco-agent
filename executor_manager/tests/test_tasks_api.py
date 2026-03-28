"""Tests for app/api/v1/tasks.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestTasksEndpoints(unittest.TestCase):
    """Test /api/v1/tasks endpoints."""

    def test_create_task_success(self) -> None:
        """Test successful task creation."""
        from app.main import app

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "task_id": "run-123",
            "session_id": "session-123",
            "status": "queued",
            "task_type": "run",
        }

        mock_service = MagicMock()
        mock_service.create_task = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.tasks.task_service",
            mock_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/tasks",
                json={
                    "user_id": "user-123",
                    "prompt": "Test prompt",
                    "config": {
                        "repo_url": "https://github.com/org/repo",
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["task_id"] == "run-123"
            mock_service.create_task.assert_called_once()
            _, kwargs = mock_service.create_task.call_args
            assert kwargs["config"] == {"repo_url": "https://github.com/org/repo"}

    def test_create_task_with_session_id(self) -> None:
        """Test task creation with existing session_id."""
        from app.main import app

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "task_id": "queue-456",
            "session_id": "existing-session",
            "status": "queued",
            "task_type": "queued_query",
        }

        mock_service = MagicMock()
        mock_service.create_task = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.tasks.task_service",
            mock_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/tasks",
                json={
                    "user_id": "user-123",
                    "prompt": "Continue conversation",
                    "session_id": "existing-session",
                    "config": {
                        "repo_url": "https://github.com/org/repo",
                    },
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["session_id"] == "existing-session"
            _, kwargs = mock_service.create_task.call_args
            assert kwargs["config"] == {"repo_url": "https://github.com/org/repo"}

    def test_create_task_with_session_id_excludes_config_defaults(self) -> None:
        """Test continuing a session does not forward schema defaults."""
        from app.main import app

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "task_id": "queue-789",
            "session_id": "existing-session",
            "status": "queued",
            "task_type": "queued_query",
        }

        mock_service = MagicMock()
        mock_service.create_task = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.tasks.task_service",
            mock_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/tasks",
                json={
                    "user_id": "user-123",
                    "prompt": "Continue conversation",
                    "session_id": "existing-session",
                    "config": {},
                },
            )

            assert response.status_code == 200
            _, kwargs = mock_service.create_task.call_args
            assert kwargs["config"] == {}

    def test_get_task_status_success(self) -> None:
        """Test successful task status retrieval."""
        from app.main import app

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "task_id": "task-123",
            "status": "running",
            "task_type": "run",
            "session_id": "session-123",
        }

        mock_service = MagicMock()
        mock_service.get_task_status = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.tasks.task_service",
            mock_service,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/tasks/task-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["task_id"] == "task-123"
            mock_service.get_task_status.assert_called_once_with("task-123")

    def test_get_task_status_by_session_success(self) -> None:
        """Test successful task status retrieval by session ID."""
        from app.main import app

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "session_id": "session-123",
            "status": "completed",
            "task_ids": ["task-1", "task-2"],
        }

        mock_service = MagicMock()
        mock_service.get_session_status = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.tasks.task_service",
            mock_service,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/tasks/session/session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["session_id"] == "session-123"
            mock_service.get_session_status.assert_called_once_with("session-123")


if __name__ == "__main__":
    unittest.main()
