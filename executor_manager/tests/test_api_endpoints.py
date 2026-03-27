"""Tests for app/api/v1 endpoints via TestClient."""

import io
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestCallbackEndpoint(unittest.TestCase):
    """Test /api/v1/callback endpoint."""

    def test_receive_callback_success(self) -> None:
        """Test successful callback processing."""
        from app.main import app

        with patch.object(
            app.dependency_overrides.get(type(app.router.routes[0].path), MagicMock()),
            "callback_service",
            None,
        ):
            with patch("app.api.v1.callback.callback_service") as mock_service:
                mock_result = MagicMock()
                mock_result.model_dump.return_value = {
                    "session_id": "sess-123",
                    "status": "received",
                    "callback_status": "completed",
                    "progress": 100,
                }
                mock_service.process_callback = AsyncMock(return_value=mock_result)

                client = TestClient(app)
                response = client.post(
                    "/api/v1/callback",
                    json={
                        "session_id": "sess-123",
                        "run_id": "run-456",
                        "status": "completed",
                        "progress": 100,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 0
                assert data["data"]["session_id"] == "sess-123"


class TestComputerEndpoint(unittest.TestCase):
    """Test /api/v1/computer/screenshots endpoint."""

    def test_upload_browser_screenshot_success(self) -> None:
        """Test successful screenshot upload."""
        from app.main import app

        with patch("app.api.v1.computer.computer_service") as mock_service:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {
                "session_id": "sess-123",
                "tool_use_id": "tool-456",
                "key": "replays/user/sess-123/browser/tool-456.png",
                "content_type": "image/png",
                "size_bytes": 100,
            }
            mock_service.upload_browser_screenshot.return_value = mock_result

            client = TestClient(app)
            fake_image = b"\x89PNG\r\n\x1a\n"  # PNG header

            response = client.post(
                "/api/v1/computer/screenshots",
                data={"session_id": "sess-123", "tool_use_id": "tool-456"},
                files={"file": ("screenshot.png", io.BytesIO(fake_image), "image/png")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["session_id"] == "sess-123"

    def test_upload_browser_screenshot_default_content_type(self) -> None:
        """Test screenshot upload with default content type."""
        from app.main import app

        with patch("app.api.v1.computer.computer_service") as mock_service:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {
                "session_id": "sess-123",
                "tool_use_id": "tool-456",
                "key": "replays/user/sess-123/browser/tool-456.png",
                "content_type": "image/png",
                "size_bytes": 100,
            }
            mock_service.upload_browser_screenshot.return_value = mock_result

            client = TestClient(app)
            fake_image = b"fake_image_data"

            # Upload without content type
            response = client.post(
                "/api/v1/computer/screenshots",
                data={"session_id": "sess-123", "tool_use_id": "tool-456"},
                files={"file": ("screenshot.png", io.BytesIO(fake_image))},
            )

            assert response.status_code == 200
            # Verify service was called
            mock_service.upload_browser_screenshot.assert_called_once()


if __name__ == "__main__":
    unittest.main()
