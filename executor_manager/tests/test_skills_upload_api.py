"""Tests for app/api/v1/skills_upload.py."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient


class TestSkillsUploadEndpoints(unittest.TestCase):
    """Test /api/v1/skills endpoints."""

    def test_submit_skill_success(self) -> None:
        """Test successful skill submission."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "ready"
        mock_export_result.workspace_files_prefix = "files/prefix/"
        mock_export_result.error = None

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"job_id": "skill-job-123"},
            "message": "Skill submission queued",
        }

        mock_client = MagicMock()
        mock_client._request = AsyncMock(return_value=mock_response)
        mock_client._trace_headers = MagicMock(return_value={})

        mock_settings = MagicMock()
        mock_settings.internal_api_token = "test-token"
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.api.v1.skills_upload.backend_client",
                mock_client,
            ),
            patch(
                "app.api.v1.skills_upload.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                    "skill_name": "my-skill",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["job_id"] == "skill-job-123"

    def test_submit_skill_export_not_ready(self) -> None:
        """Test skill submission when export is not ready."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "error"
        mock_export_result.workspace_files_prefix = None
        mock_export_result.error = "Export failed"

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        mock_settings = MagicMock()
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "Export failed" in data["message"]

    def test_submit_skill_export_missing_files(self) -> None:
        """Test skill submission when export has no files."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "ready"
        mock_export_result.workspace_files_prefix = "   "  # Empty/whitespace
        mock_export_result.error = None

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        mock_settings = MagicMock()
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "missing files" in data["message"]

    def test_submit_skill_backend_http_error(self) -> None:
        """Test skill submission with backend HTTP error."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "ready"
        mock_export_result.workspace_files_prefix = "files/prefix/"
        mock_export_result.error = None

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        # Create mock HTTP response
        mock_http_response = MagicMock()
        mock_http_response.status_code = 500
        mock_http_response.text = "Internal Server Error"
        mock_http_response.json.return_value = {"message": "Backend service error"}

        mock_client = MagicMock()
        mock_client._request = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=mock_http_response,
            )
        )
        mock_client._trace_headers = MagicMock(return_value={})

        mock_settings = MagicMock()
        mock_settings.internal_api_token = "test-token"
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.api.v1.skills_upload.backend_client",
                mock_client,
            ),
            patch(
                "app.api.v1.skills_upload.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 500
            data = response.json()
            assert "Backend service error" in data["message"]

    def test_submit_skill_backend_http_error_no_json(self) -> None:
        """Test skill submission with backend HTTP error (no JSON response)."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "ready"
        mock_export_result.workspace_files_prefix = "files/prefix/"
        mock_export_result.error = None

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        # Create mock HTTP response that fails JSON parsing
        mock_http_response = MagicMock()
        mock_http_response.status_code = 503
        mock_http_response.text = "Service Unavailable"
        mock_http_response.json.side_effect = Exception("Not JSON")

        mock_client = MagicMock()
        mock_client._request = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Service unavailable",
                request=MagicMock(),
                response=mock_http_response,
            )
        )
        mock_client._trace_headers = MagicMock(return_value={})

        mock_settings = MagicMock()
        mock_settings.internal_api_token = "test-token"
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.api.v1.skills_upload.backend_client",
                mock_client,
            ),
            patch(
                "app.api.v1.skills_upload.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 503
            data = response.json()
            assert "Service Unavailable" in data["message"]

    def test_submit_skill_backend_http_error_with_detail(self) -> None:
        """Test skill submission with backend HTTP error using detail field."""
        from app.main import app

        mock_export_result = MagicMock()
        mock_export_result.workspace_export_status = "ready"
        mock_export_result.workspace_files_prefix = "files/prefix/"
        mock_export_result.error = None

        mock_export_service = MagicMock()
        mock_export_service.stage_skill_submission_folder = MagicMock(
            return_value="/staged/skill-folder"
        )
        mock_export_service.export_workspace_folder = MagicMock(
            return_value=mock_export_result
        )

        # Create mock HTTP response with detail field
        mock_http_response = MagicMock()
        mock_http_response.status_code = 400
        mock_http_response.text = "Bad Request"
        mock_http_response.json.return_value = {"detail": "Invalid skill configuration"}

        mock_client = MagicMock()
        mock_client._request = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Bad request",
                request=MagicMock(),
                response=mock_http_response,
            )
        )
        mock_client._trace_headers = MagicMock(return_value={})

        mock_settings = MagicMock()
        mock_settings.internal_api_token = "test-token"
        mock_settings.callback_token = "callback-token"

        with (
            patch(
                "app.api.v1.skills_upload.workspace_export_service",
                mock_export_service,
            ),
            patch(
                "app.api.v1.skills_upload.backend_client",
                mock_client,
            ),
            patch(
                "app.api.v1.skills_upload.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.core.deps.get_settings",
                return_value=mock_settings,
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/skills/submit",
                json={
                    "session_id": "session-123",
                    "folder_path": "/workspace/skill-folder",
                },
                headers={"Authorization": "Bearer callback-token"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "Invalid skill configuration" in data["message"]


if __name__ == "__main__":
    unittest.main()
