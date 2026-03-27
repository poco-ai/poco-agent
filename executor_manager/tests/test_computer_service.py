import unittest
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.computer_service import ComputerService, _sanitize_token


class TestSanitizeToken(unittest.TestCase):
    """Test _sanitize_token helper function."""

    def test_sanitize_simple_token(self) -> None:
        """Test sanitizing a simple token."""
        result = _sanitize_token("abc123")
        assert result == "abc123"

    def test_sanitize_token_with_spaces(self) -> None:
        """Test sanitizing token with spaces."""
        result = _sanitize_token("  abc123  ")
        assert result == "abc123"

    def test_sanitize_token_with_special_chars(self) -> None:
        """Test sanitizing token with special characters."""
        result = _sanitize_token("abc@123#def")
        assert result == "abc_123_def"

    def test_sanitize_token_preserves_allowed_chars(self) -> None:
        """Test that allowed characters are preserved."""
        result = _sanitize_token("abc.123-456_789")
        assert result == "abc.123-456_789"

    def test_sanitize_token_strips_leading_trailing_special(self) -> None:
        """Test that leading/trailing special chars are stripped."""
        result = _sanitize_token("...abc...")
        assert result == "abc"

    def test_sanitize_token_empty_string(self) -> None:
        """Test sanitizing empty string."""
        result = _sanitize_token("")
        assert result == "unknown"

    def test_sanitize_token_none(self) -> None:
        """Test sanitizing None value."""
        result = _sanitize_token(None)  # type: ignore
        assert result == "unknown"

    def test_sanitize_token_only_special_chars(self) -> None:
        """Test sanitizing string with only special chars."""
        result = _sanitize_token("@#$%")
        assert result == "unknown"

    def test_sanitize_token_whitespace_only(self) -> None:
        """Test sanitizing whitespace only string."""
        result = _sanitize_token("   ")
        assert result == "unknown"

    def test_sanitize_token_with_dots_and_dashes_at_edges(self) -> None:
        """Test stripping dots and dashes at edges."""
        result = _sanitize_token("-abc.def-")
        assert result == "abc.def"


class TestComputerServiceInit(unittest.TestCase):
    """Test ComputerService.__init__."""

    def test_init_with_defaults(self) -> None:
        with (
            patch(
                "app.services.computer_service.WorkspaceManager"
            ) as mock_workspace_cls,
            patch("app.services.computer_service.S3StorageService") as mock_storage_cls,
        ):
            mock_workspace_cls.return_value = MagicMock()
            mock_storage_cls.return_value = MagicMock()

            ComputerService()

            mock_workspace_cls.assert_called_once()
            mock_storage_cls.assert_called_once()

    def test_init_with_dependencies(self) -> None:
        mock_workspace = MagicMock()
        mock_storage = MagicMock()

        service = ComputerService(
            workspace_manager=mock_workspace,
            storage_service=mock_storage,
        )

        assert service._workspace_manager is mock_workspace
        assert service._storage_service is mock_storage


class TestComputerServiceUploadBrowserScreenshot(unittest.TestCase):
    """Test ComputerService.upload_browser_screenshot."""

    def _create_service(self) -> ComputerService:
        mock_workspace = MagicMock()
        mock_storage = MagicMock()
        return ComputerService(
            workspace_manager=mock_workspace,
            storage_service=mock_storage,
        )

    def test_upload_success(self) -> None:
        """Test successful screenshot upload."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool-789",
            content_type="image/png",
            data=b"fake_png_data",
        )

        assert result.session_id == "session-456"
        assert result.tool_use_id == "tool-789"
        assert result.key == "replays/user-123/session-456/browser/tool-789.png"
        assert result.content_type == "image/png"
        assert result.size_bytes == len(b"fake_png_data")

        service._storage_service.put_object.assert_called_once()

    def test_upload_with_custom_content_type(self) -> None:
        """Test upload with custom content type."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool-789",
            content_type="image/jpeg",
            data=b"fake_jpeg_data",
        )

        assert result.content_type == "image/jpeg"
        call_kwargs = service._storage_service.put_object.call_args[1]
        assert call_kwargs["content_type"] == "image/jpeg"

    def test_upload_with_empty_content_type(self) -> None:
        """Test upload with empty content type defaults to png."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool-789",
            content_type="",
            data=b"fake_data",
        )

        assert result.content_type == "image/png"

    def test_upload_with_none_content_type(self) -> None:
        """Test upload with None content type defaults to png."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool-789",
            content_type=None,  # type: ignore
            data=b"fake_data",
        )

        assert result.content_type == "image/png"

    def test_upload_sanitizes_session_id(self) -> None:
        """Test that session_id is sanitized."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session@456#test",
            tool_use_id="tool-789",
            content_type="image/png",
            data=b"fake_data",
        )

        assert "session_456_test" in result.key

    def test_upload_sanitizes_tool_use_id(self) -> None:
        """Test that tool_use_id is sanitized."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool@789#test",
            content_type="image/png",
            data=b"fake_data",
        )

        assert "tool_789_test" in result.key

    def test_upload_raises_when_user_not_found(self) -> None:
        """Test that upload raises when user_id cannot be resolved."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            service.upload_browser_screenshot(
                session_id="unknown-session",
                tool_use_id="tool-789",
                content_type="image/png",
                data=b"fake_data",
            )

        assert ctx.exception.error_code == ErrorCode.NOT_FOUND
        assert "Unable to resolve user_id" in ctx.exception.message
        assert ctx.exception.details["session_id"] == "unknown-session"

    def test_upload_calls_put_object_correctly(self) -> None:
        """Test that put_object is called with correct parameters."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        service.upload_browser_screenshot(
            session_id="session-456",
            tool_use_id="tool-789",
            content_type="image/png",
            data=b"test_data",
        )

        call_kwargs = service._storage_service.put_object.call_args[1]
        assert call_kwargs["key"] == "replays/user-123/session-456/browser/tool-789.png"
        assert call_kwargs["body"] == b"test_data"
        assert call_kwargs["content_type"] == "image/png"

    def test_upload_key_format(self) -> None:
        """Test that the key format is correct."""
        service = self._create_service()
        service._workspace_manager.resolve_user_id.return_value = "user-123"

        result = service.upload_browser_screenshot(
            session_id="sess",
            tool_use_id="tool",
            content_type="image/png",
            data=b"data",
        )

        # Key format: replays/{user_id}/{session_id}/browser/{tool_use_id}.png
        assert result.key.startswith("replays/")
        assert "/browser/" in result.key
        assert result.key.endswith(".png")


if __name__ == "__main__":
    unittest.main()
