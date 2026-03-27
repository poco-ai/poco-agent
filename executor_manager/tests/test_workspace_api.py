"""Tests for app/api/v1/workspace.py."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestWorkspaceEndpoints(unittest.TestCase):
    """Test /api/v1/workspace endpoints."""

    def test_get_workspace_stats_success(self) -> None:
        """Test successful workspace stats retrieval."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.get_disk_usage.return_value = {
            "total_size_bytes": 1024000,
            "workspaces_count": 5,
        }

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/workspace/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["total_size_bytes"] == 1024000
            mock_manager.get_disk_usage.assert_called_once()

    def test_get_user_workspaces_success(self) -> None:
        """Test successful user workspaces retrieval."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.get_user_workspaces.return_value = [
            {"session_id": "session-1", "path": "/workspace/user-123/session-1"},
            {"session_id": "session-2", "path": "/workspace/user-123/session-2"},
        ]

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/workspace/users/user-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 2
            mock_manager.get_user_workspaces.assert_called_once_with("user-123")

    def test_archive_workspace_success(self) -> None:
        """Test successful workspace archival."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.archive_workspace.return_value = (
            "/archive/user-123/session-1.tar.gz"
        )

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.post("/api/v1/workspace/archive/user-123/session-1")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["archive_path"] == "/archive/user-123/session-1.tar.gz"
            mock_manager.archive_workspace.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
                keep_days=7,
            )

    def test_archive_workspace_with_custom_keep_days(self) -> None:
        """Test workspace archival with custom keep_days."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.archive_workspace.return_value = (
            "/archive/user-123/session-1.tar.gz"
        )

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/workspace/archive/user-123/session-1?keep_days=30"
            )

            assert response.status_code == 200
            mock_manager.archive_workspace.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
                keep_days=30,
            )

    def test_archive_workspace_failure(self) -> None:
        """Test workspace archival failure."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.archive_workspace.return_value = None

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/v1/workspace/archive/user-123/session-1")

            assert response.status_code == 400
            data = response.json()
            assert data["code"] != 0

    def test_delete_workspace_success(self) -> None:
        """Test successful workspace deletion."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.delete_workspace.return_value = True

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.delete("/api/v1/workspace/user-123/session-1")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["user_id"] == "user-123"
            assert data["data"]["session_id"] == "session-1"
            mock_manager.delete_workspace.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
                force=False,
            )

    def test_delete_workspace_with_force(self) -> None:
        """Test workspace deletion with force flag."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.delete_workspace.return_value = True

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.delete("/api/v1/workspace/user-123/session-1?force=true")

            assert response.status_code == 200
            mock_manager.delete_workspace.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
                force=True,
            )

    def test_delete_workspace_failure(self) -> None:
        """Test workspace deletion failure."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.delete_workspace.return_value = False

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.delete("/api/v1/workspace/user-123/session-1")

            assert response.status_code == 400
            data = response.json()
            assert data["code"] != 0

    def test_list_workspace_files_success(self) -> None:
        """Test successful workspace files listing."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.list_workspace_files.return_value = [
            {"name": "file1.py", "path": "file1.py", "type": "file"},
            {"name": "src", "path": "src", "type": "directory"},
        ]

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/workspace/files/user-123/session-1")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 2
            mock_manager.list_workspace_files.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
            )

    def test_get_workspace_file_success(self) -> None:
        """Test successful workspace file retrieval."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.resolve_workspace_file.return_value = Path(
            "/workspace/user-123/session-1/main.py"
        )

        # Mock FileResponse to avoid file system access
        with (
            patch(
                "app.api.v1.workspace.workspace_manager",
                mock_manager,
            ),
            patch("app.api.v1.workspace.FileResponse") as mock_file_response,
        ):
            mock_file_response.return_value = MagicMock()

            client = TestClient(app)
            client.get("/api/v1/workspace/file/user-123/session-1?path=main.py")

            # Verify the manager was called correctly
            mock_manager.resolve_workspace_file.assert_called_once_with(
                user_id="user-123",
                session_id="session-1",
                file_path="main.py",
            )
            # FileResponse should have been called with the resolved path
            mock_file_response.assert_called_once()

    def test_get_workspace_file_not_found(self) -> None:
        """Test workspace file not found."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.resolve_workspace_file.return_value = None

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/api/v1/workspace/file/user-123/session-1?path=nonexistent.py"
            )

            assert response.status_code == 400
            data = response.json()
            assert data["code"] != 0

    def test_get_user_workspaces_empty(self) -> None:
        """Test user workspaces when none exist."""
        from app.main import app

        mock_manager = MagicMock()
        mock_manager.get_user_workspaces.return_value = []

        with patch(
            "app.api.v1.workspace.workspace_manager",
            mock_manager,
        ):
            client = TestClient(app)
            response = client.get("/api/v1/workspace/users/user-no-workspaces")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"] == []


if __name__ == "__main__":
    unittest.main()
