"""Tests for app/main.py."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestCreateApp(unittest.TestCase):
    """Test create_app function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI instance."""
        with (
            patch("app.main.configure_logging") as mock_logging,
            patch("app.main.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.app_name = "test-app"
            mock_settings.app_version = "1.0.0"
            mock_settings.debug = False
            mock_settings.uvicorn_access_log = False
            mock_settings.cors_origins = ["*"]
            mock_get_settings.return_value = mock_settings

            from app.main import create_app

            app = create_app()

            assert app is not None
            assert app.title == "test-app"
            assert app.version == "1.0.0"
            mock_logging.assert_called_once()

    def test_create_app_sets_debug_mode(self) -> None:
        """Test that create_app sets debug mode from settings."""
        with (
            patch("app.main.configure_logging") as _mock_logging,
            patch("app.main.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.app_name = "test-app"
            mock_settings.app_version = "1.0.0"
            mock_settings.debug = True
            mock_settings.uvicorn_access_log = True
            mock_settings.cors_origins = ["*"]
            mock_get_settings.return_value = mock_settings

            from app.main import create_app

            app = create_app()

            assert app.debug is True


class TestAppRoutes(unittest.TestCase):
    """Test API routes via TestClient."""

    def test_root_endpoint(self) -> None:
        """Test root endpoint returns service info."""
        # Import the app directly (uses real settings)
        from app.main import app

        client = TestClient(app)

        response = client.get("/api/v1/")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "service" in data["data"]
        assert data["data"]["status"] == "running"

    def test_health_endpoint(self) -> None:
        """Test health endpoint returns health info."""
        from app.main import app

        client = TestClient(app)

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "service" in data["data"]
        assert data["data"]["status"] == "healthy"
        assert "scheduler_running" in data["data"]


if __name__ == "__main__":
    unittest.main()
