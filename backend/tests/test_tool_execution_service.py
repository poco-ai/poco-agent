import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.tool_execution import ToolExecutionDeltaResponse
from app.services.tool_execution_service import ToolExecutionService


class TestToolExecutionServiceGetToolExecutions(unittest.TestCase):
    """Test ToolExecutionService.get_tool_executions."""

    def setUp(self) -> None:
        self.service = ToolExecutionService()
        self.db = MagicMock()
        self.session_id = uuid.uuid4()

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_get_tool_executions_success(self, mock_repo: MagicMock) -> None:
        mock_executions = [MagicMock(), MagicMock()]
        mock_repo.list_by_session.return_value = mock_executions

        result = self.service.get_tool_executions(
            self.db, self.session_id, limit=100, offset=10
        )

        mock_repo.list_by_session.assert_called_once_with(
            self.db, self.session_id, limit=100, offset=10
        )
        self.assertEqual(result, mock_executions)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_get_tool_executions_default_params(self, mock_repo: MagicMock) -> None:
        mock_executions = []
        mock_repo.list_by_session.return_value = mock_executions

        self.service.get_tool_executions(self.db, self.session_id)

        mock_repo.list_by_session.assert_called_once()
        call_args = mock_repo.list_by_session.call_args
        self.assertEqual(call_args.kwargs["limit"], 500)
        self.assertEqual(call_args.kwargs["offset"], 0)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_get_tool_executions_clamps_limit(self, mock_repo: MagicMock) -> None:
        mock_repo.list_by_session.return_value = []

        self.service.get_tool_executions(self.db, self.session_id, limit=-5)

        call_args = mock_repo.list_by_session.call_args
        self.assertEqual(call_args.kwargs["limit"], 1)


class TestToolExecutionServiceGetToolExecution(unittest.TestCase):
    """Test ToolExecutionService.get_tool_execution."""

    def setUp(self) -> None:
        self.service = ToolExecutionService()
        self.db = MagicMock()
        self.execution_id = uuid.uuid4()

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_get_tool_execution_found(self, mock_repo: MagicMock) -> None:
        mock_execution = MagicMock()
        mock_repo.get_by_id.return_value = mock_execution

        result = self.service.get_tool_execution(self.db, self.execution_id)

        mock_repo.get_by_id.assert_called_once_with(self.db, self.execution_id)
        self.assertEqual(result, mock_execution)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_get_tool_execution_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.get_tool_execution(self.db, self.execution_id)

        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)


class TestToolExecutionServiceGetToolExecutionsDelta(unittest.TestCase):
    """Test ToolExecutionService.get_tool_executions_delta."""

    def setUp(self) -> None:
        self.service = ToolExecutionService()
        self.db = MagicMock()
        self.session_id = uuid.uuid4()

    def _make_execution(self, **kwargs) -> MagicMock:
        mock = MagicMock()
        mock.id = kwargs.get("id", uuid.uuid4())
        mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
        mock.tool_input = kwargs.get("tool_input", {})
        mock.tool_output = kwargs.get("tool_output", {})
        mock.session_id = kwargs.get("session_id", uuid.uuid4())
        mock.message_id = kwargs.get("message_id", 1)
        mock.tool_use_id = kwargs.get("tool_use_id", "tool-123")
        mock.tool_name = kwargs.get("tool_name", "read_file")
        mock.is_error = kwargs.get("is_error", False)
        mock.duration_ms = kwargs.get("duration_ms", None)
        mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        return mock

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_delta_no_cursor(self, mock_repo: MagicMock) -> None:
        mock_repo.list_by_session_after_cursor.return_value = []

        result = self.service.get_tool_executions_delta(self.db, self.session_id)

        self.assertIsInstance(result, ToolExecutionDeltaResponse)
        self.assertEqual(result.items, [])
        self.assertFalse(result.has_more)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_delta_with_cursor(self, mock_repo: MagicMock) -> None:
        cursor_time = datetime.now(timezone.utc)
        cursor_id = uuid.uuid4()
        mock_repo.list_by_session_after_cursor.return_value = []

        result = self.service.get_tool_executions_delta(
            self.db,
            self.session_id,
            after_created_at=cursor_time,
            after_id=cursor_id,
        )

        self.assertEqual(result.next_after_created_at, cursor_time)
        self.assertEqual(result.next_after_id, cursor_id)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_delta_with_results(self, mock_repo: MagicMock) -> None:
        exec1 = self._make_execution()
        exec2 = self._make_execution()
        mock_repo.list_by_session_after_cursor.return_value = [exec1, exec2]

        result = self.service.get_tool_executions_delta(self.db, self.session_id)

        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.next_after_created_at, exec2.updated_at)
        self.assertEqual(result.next_after_id, exec2.id)

    @patch("app.services.tool_execution_service.ToolExecutionRepository")
    def test_delta_has_more(self, mock_repo: MagicMock) -> None:
        # Return more items than limit
        executions = [self._make_execution() for _ in range(202)]
        mock_repo.list_by_session_after_cursor.return_value = executions

        result = self.service.get_tool_executions_delta(
            self.db, self.session_id, limit=200
        )

        self.assertTrue(result.has_more)
        # safe_limit = min(200, 2000) = 200, so we get 200 items
        self.assertEqual(len(result.items), 200)


if __name__ == "__main__":
    unittest.main()
