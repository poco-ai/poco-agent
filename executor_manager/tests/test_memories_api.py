"""Tests for app/api/v1/memories.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestMemoriesEndpoints(unittest.TestCase):
    """Test /api/v1/memories endpoints."""

    def test_create_memories_success(self) -> None:
        """Test successful memory creation."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.create_memory = AsyncMock(
            return_value={"job_id": "job-123", "status": "queued"}
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/memories",
                json={
                    "session_id": "session-123",
                    "messages": [{"role": "user", "content": "test message"}],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["job_id"] == "job-123"
            mock_client.create_memory.assert_called_once()

    def test_get_memory_create_job_success(self) -> None:
        """Test successful memory create job retrieval."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.get_memory_create_job = AsyncMock(
            return_value={"job_id": "job-123", "status": "completed"}
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get(
                "/api/v1/memories/jobs/job-123?session_id=session-123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["job_id"] == "job-123"
            mock_client.get_memory_create_job.assert_called_once_with(
                session_id="session-123",
                job_id="job-123",
            )

    def test_list_memories_success(self) -> None:
        """Test successful memories listing."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.list_memories = AsyncMock(
            return_value=[
                {"id": "mem-1", "content": "memory 1"},
                {"id": "mem-2", "content": "memory 2"},
            ]
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/memories?session_id=session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 2
            mock_client.list_memories.assert_called_once_with(session_id="session-123")

    def test_search_memories_success(self) -> None:
        """Test successful memories search."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.search_memories = AsyncMock(
            return_value=[{"id": "mem-1", "content": "matched memory"}]
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/memories/search",
                json={
                    "session_id": "session-123",
                    "query": "test query",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 1
            mock_client.search_memories.assert_called_once()

    def test_get_memory_success(self) -> None:
        """Test successful single memory retrieval."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.get_memory = AsyncMock(
            return_value={"id": "mem-123", "content": "test memory"}
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/memories/mem-123?session_id=session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["id"] == "mem-123"
            mock_client.get_memory.assert_called_once_with(
                session_id="session-123",
                memory_id="mem-123",
            )

    def test_update_memory_success(self) -> None:
        """Test successful memory update."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.update_memory = AsyncMock(
            return_value={"id": "mem-123", "content": "updated content"}
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.put(
                "/api/v1/memories/mem-123",
                json={
                    "session_id": "session-123",
                    "text": "updated memory text",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            mock_client.update_memory.assert_called_once()

    def test_get_memory_history_success(self) -> None:
        """Test successful memory history retrieval."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.get_memory_history = AsyncMock(
            return_value=[
                {"version": 1, "content": "old"},
                {"version": 2, "content": "new"},
            ]
        )

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.get(
                "/api/v1/memories/mem-123/history?session_id=session-123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 2
            mock_client.get_memory_history.assert_called_once_with(
                session_id="session-123",
                memory_id="mem-123",
            )

    def test_delete_memory_success(self) -> None:
        """Test successful memory deletion."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.delete_memory = AsyncMock(return_value={"deleted": True})

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.delete("/api/v1/memories/mem-123?session_id=session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            mock_client.delete_memory.assert_called_once_with(
                session_id="session-123",
                memory_id="mem-123",
            )

    def test_delete_all_memories_success(self) -> None:
        """Test successful deletion of all memories."""
        from app.main import app

        mock_client = MagicMock()
        mock_client.delete_all_memories = AsyncMock(return_value={"deleted_count": 5})

        with patch(
            "app.api.v1.memories.backend_client",
            mock_client,
        ):
            client = TestClient(app)
            response = client.delete("/api/v1/memories?session_id=session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            mock_client.delete_all_memories.assert_called_once_with(
                session_id="session-123"
            )


if __name__ == "__main__":
    unittest.main()
