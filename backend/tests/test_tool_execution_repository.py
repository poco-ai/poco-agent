import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.repositories.tool_execution_repository import ToolExecutionRepository


def create_mock_tool_execution(
    execution_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    message_id: int = 1,
    tool_use_id: str = "tool-123",
    tool_name: str = "read_file",
    tool_input: dict | None = None,
    tool_output: dict | None = None,
    result_message_id: int | None = None,
    is_error: bool = False,
    duration_ms: int | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> MagicMock:
    """Helper to create a mock ToolExecution."""
    mock = MagicMock()
    mock.id = execution_id or uuid.uuid4()
    mock.session_id = session_id or uuid.uuid4()
    mock.message_id = message_id
    mock.tool_use_id = tool_use_id
    mock.tool_name = tool_name
    mock.tool_input = tool_input
    mock.tool_output = tool_output
    mock.result_message_id = result_message_id
    mock.is_error = is_error
    mock.duration_ms = duration_ms
    mock.created_at = created_at or datetime.now(timezone.utc)
    mock.updated_at = updated_at or datetime.now(timezone.utc)
    return mock


class TestToolExecutionRepositoryCreate(unittest.TestCase):
    """Test ToolExecutionRepository.create."""

    def test_create_with_defaults(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()

        result = ToolExecutionRepository.create(
            mock_db,
            session_id,
            message_id=1,
            tool_use_id="tool-1",
            tool_name="read_file",
        )

        assert result.session_id == session_id
        assert result.message_id == 1
        assert result.tool_use_id == "tool-1"
        assert result.tool_name == "read_file"
        assert result.tool_input is None
        assert result.tool_output is None
        assert result.is_error is False
        mock_db.add.assert_called_once()

    def test_create_with_all_params(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()

        result = ToolExecutionRepository.create(
            mock_db,
            session_id,
            message_id=1,
            tool_use_id="tool-1",
            tool_name="write_file",
            tool_input={"path": "/tmp/file"},
            tool_output={"content": "written"},
            result_message_id=2,
            is_error=True,
            duration_ms=100,
        )

        assert result.tool_input == {"path": "/tmp/file"}
        assert result.tool_output == {"content": "written"}
        assert result.result_message_id == 2
        assert result.is_error is True
        assert result.duration_ms == 100

    def test_create_with_none_tool_use_id(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()

        result = ToolExecutionRepository.create(
            mock_db, session_id, message_id=1, tool_use_id=None, tool_name="test"
        )

        assert result.tool_use_id is None


class TestToolExecutionRepositoryGetById(unittest.TestCase):
    """Test ToolExecutionRepository.get_by_id."""

    def test_get_by_id_found(self) -> None:
        mock_db = MagicMock()
        execution_id = uuid.uuid4()
        mock_execution = create_mock_tool_execution(execution_id=execution_id)

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_execution
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.get_by_id(mock_db, execution_id)

        assert result == mock_execution

    def test_get_by_id_not_found(self) -> None:
        mock_db = MagicMock()
        execution_id = uuid.uuid4()

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.get_by_id(mock_db, execution_id)

        assert result is None


class TestToolExecutionRepositoryGetBySessionAndToolUseId(unittest.TestCase):
    """Test ToolExecutionRepository.get_by_session_and_tool_use_id."""

    def test_get_by_session_and_tool_use_id_found(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_execution = create_mock_tool_execution(session_id=session_id)

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_execution
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.get_by_session_and_tool_use_id(
            mock_db, session_id, "tool-123"
        )

        assert result == mock_execution

    def test_get_by_session_and_tool_use_id_not_found(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.get_by_session_and_tool_use_id(
            mock_db, session_id, "nonexistent"
        )

        assert result is None


class TestToolExecutionRepositoryListBySession(unittest.TestCase):
    """Test ToolExecutionRepository.list_by_session."""

    def test_list_by_session_default_params(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_executions = [
            create_mock_tool_execution(session_id=session_id) for _ in range(3)
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.limit.return_value.offset.return_value.all.return_value = (
            mock_executions
        )
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session(mock_db, session_id)

        assert result == mock_executions
        mock_order.limit.assert_called_once_with(100)

    def test_list_by_session_with_pagination(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_executions = [
            create_mock_tool_execution(session_id=session_id) for _ in range(5)
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.limit.return_value.offset.return_value.all.return_value = (
            mock_executions
        )
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session(
            mock_db, session_id, limit=10, offset=5
        )

        assert result == mock_executions
        mock_order.limit.assert_called_once_with(10)


class TestToolExecutionRepositoryListBySessionAndToolName(unittest.TestCase):
    """Test ToolExecutionRepository.list_by_session_and_tool_name."""

    def test_list_by_session_and_tool_name(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_executions = [
            create_mock_tool_execution(session_id=session_id, tool_name="read_file")
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = mock_executions
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session_and_tool_name(
            mock_db, session_id=session_id, tool_name="read_file"
        )

        assert result == mock_executions


class TestToolExecutionRepositoryListBySessionAfterCursor(unittest.TestCase):
    """Test ToolExecutionRepository.list_by_session_after_cursor."""

    def test_list_without_cursor(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_executions = [create_mock_tool_execution(session_id=session_id)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_limit.all.return_value = mock_executions
        mock_order.limit.return_value = mock_limit
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session_after_cursor(
            mock_db, session_id
        )

        assert result == mock_executions

    def test_list_with_created_at_cursor(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        cursor_time = datetime.now(timezone.utc)
        mock_executions = [create_mock_tool_execution(session_id=session_id)]

        mock_query = MagicMock()
        mock_filter_step1 = MagicMock()
        mock_filter_step2 = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_limit.all.return_value = mock_executions
        mock_order.limit.return_value = mock_limit
        mock_filter_step2.order_by.return_value = mock_order
        mock_filter_step1.filter.return_value = mock_filter_step2
        mock_query.filter.return_value = mock_filter_step1
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session_after_cursor(
            mock_db, session_id, after_created_at=cursor_time
        )

        assert result == mock_executions

    def test_list_with_full_cursor(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        cursor_time = datetime.now(timezone.utc)
        cursor_id = uuid.uuid4()
        mock_executions = [create_mock_tool_execution(session_id=session_id)]

        mock_query = MagicMock()
        mock_filter_step1 = MagicMock()
        mock_filter_step2 = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_limit.all.return_value = mock_executions
        mock_order.limit.return_value = mock_limit
        mock_filter_step2.order_by.return_value = mock_order
        mock_filter_step1.filter.return_value = mock_filter_step2
        mock_query.filter.return_value = mock_filter_step1
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_session_after_cursor(
            mock_db, session_id, after_created_at=cursor_time, after_id=cursor_id
        )

        assert result == mock_executions


class TestToolExecutionRepositoryListUnfinishedBySession(unittest.TestCase):
    """Test ToolExecutionRepository.list_unfinished_by_session."""

    def test_list_unfinished(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()
        mock_executions = [
            create_mock_tool_execution(session_id=session_id, tool_output=None)
        ]

        mock_query = MagicMock()
        mock_filter_step1 = MagicMock()
        mock_filter_step2 = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = mock_executions
        mock_filter_step2.order_by.return_value = mock_order
        mock_filter_step1.filter.return_value = mock_filter_step2
        mock_query.filter.return_value = mock_filter_step1
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_unfinished_by_session(mock_db, session_id)

        assert result == mock_executions


class TestToolExecutionRepositoryListByMessage(unittest.TestCase):
    """Test ToolExecutionRepository.list_by_message."""

    def test_list_by_message(self) -> None:
        mock_db = MagicMock()
        mock_executions = [create_mock_tool_execution(message_id=1)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = mock_executions
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_message(mock_db, 1)

        assert result == mock_executions


class TestToolExecutionRepositoryCountBySession(unittest.TestCase):
    """Test ToolExecutionRepository.count_by_session."""

    def test_count_by_session(self) -> None:
        mock_db = MagicMock()
        session_id = uuid.uuid4()

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.count.return_value = 5
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.count_by_session(mock_db, session_id)

        assert result == 5


class TestToolExecutionRepositoryListByIds(unittest.TestCase):
    """Test ToolExecutionRepository.list_by_ids."""

    def test_list_by_ids_empty(self) -> None:
        mock_db = MagicMock()

        result = ToolExecutionRepository.list_by_ids(mock_db, [])

        assert result == []

    def test_list_by_ids(self) -> None:
        mock_db = MagicMock()
        ids = [uuid.uuid4() for _ in range(3)]
        mock_executions = [
            create_mock_tool_execution(execution_id=execution_id)
            for execution_id in ids
        ]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = mock_executions
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        result = ToolExecutionRepository.list_by_ids(mock_db, ids)

        assert result == mock_executions


if __name__ == "__main__":
    unittest.main()
