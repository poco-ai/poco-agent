import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.session_queue_service import SessionQueueService


class TestSessionQueueServiceHelpers(unittest.TestCase):
    """Test SessionQueueService helper methods."""

    def test_normalize_prompt_valid(self) -> None:
        result = SessionQueueService._normalize_prompt("  Hello World  ")
        self.assertEqual(result, "Hello World")

    def test_normalize_prompt_empty(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SessionQueueService._normalize_prompt("")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_normalize_prompt_whitespace(self) -> None:
        with self.assertRaises(AppException) as ctx:
            SessionQueueService._normalize_prompt("   ")

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)

    def test_extract_session_config_none(self) -> None:
        result = SessionQueueService.extract_session_config(None)
        self.assertIsNone(result)

    def test_extract_session_config_not_dict(self) -> None:
        result = SessionQueueService.extract_session_config("not a dict")
        self.assertIsNone(result)

    def test_extract_session_config_removes_input_files(self) -> None:
        config = {"model": "claude", "input_files": ["file1.txt"]}
        result = SessionQueueService.extract_session_config(config)

        self.assertEqual(result, {"model": "claude"})
        self.assertNotIn("input_files", result)

    def test_extract_session_config_empty_result(self) -> None:
        config = {"input_files": ["file1.txt"]}
        result = SessionQueueService.extract_session_config(config)
        self.assertIsNone(result)


class TestSessionQueueServiceClearExecutionState(unittest.TestCase):
    """Test SessionQueueService.clear_execution_state."""

    def test_clears_workspace_fields(self) -> None:
        mock_session = MagicMock()
        mock_session.state_patch = {"key": "value"}
        mock_session.workspace_archive_url = "https://archive.url"
        mock_session.workspace_files_prefix = "prefix/"
        mock_session.workspace_manifest_key = "manifest-key"
        mock_session.workspace_archive_key = "archive-key"
        mock_session.workspace_export_status = "completed"

        SessionQueueService.clear_execution_state(mock_session)

        self.assertEqual(mock_session.state_patch, {})
        self.assertIsNone(mock_session.workspace_archive_url)
        self.assertIsNone(mock_session.workspace_files_prefix)
        self.assertIsNone(mock_session.workspace_manifest_key)
        self.assertIsNone(mock_session.workspace_archive_key)
        self.assertIsNone(mock_session.workspace_export_status)


class TestSessionQueueServiceListItems(unittest.TestCase):
    """Test SessionQueueService.list_items."""

    def test_list_items(self) -> None:
        service = SessionQueueService()
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch(
            "app.services.session_queue_service.SessionQueueItemRepository"
        ) as mock_repo:
            mock_items = [MagicMock(), MagicMock()]
            mock_repo.list_active_by_session.return_value = mock_items

            result = service.list_items(db, session_id)

            mock_repo.list_active_by_session.assert_called_once_with(db, session_id)
            self.assertEqual(result, mock_items)


if __name__ == "__main__":
    unittest.main()
