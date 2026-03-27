import unittest
import uuid
from unittest.mock import MagicMock

from app.models.agent_message import AgentMessage
from app.repositories.message_repository import MessageRepository


class TestMessageRepositoryCreate(unittest.TestCase):
    """Test MessageRepository.create method."""

    def test_create_with_defaults(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        content = {"text": "Hello"}

        result = MessageRepository.create(db, session_id, "user", content)

        self.assertEqual(result.session_id, session_id)
        self.assertEqual(result.role, "user")
        self.assertEqual(result.content, content)
        self.assertIsNone(result.text_preview)
        db.add.assert_called_once()

    def test_create_with_text_preview(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        content = {"text": "Hello world"}

        result = MessageRepository.create(
            db, session_id, "user", content, text_preview="Hello world"
        )

        self.assertEqual(result.text_preview, "Hello world")


class TestMessageRepositoryGetById(unittest.TestCase):
    """Test MessageRepository.get_by_id method."""

    def test_get_by_id_found(self) -> None:
        db = MagicMock()
        mock_message = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_message

        result = MessageRepository.get_by_id(db, 1)

        self.assertEqual(result, mock_message)
        db.query.assert_called_once_with(AgentMessage)

    def test_get_by_id_not_found(self) -> None:
        db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = MessageRepository.get_by_id(db, 999)

        self.assertIsNone(result)


class TestMessageRepositoryGetLatestBySession(unittest.TestCase):
    """Test MessageRepository.get_latest_by_session method."""

    def test_get_latest_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_message = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.first.return_value = mock_message

        result = MessageRepository.get_latest_by_session(db, session_id)

        self.assertEqual(result, mock_message)

    def test_get_latest_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.first.return_value = None

        result = MessageRepository.get_latest_by_session(db, session_id)

        self.assertIsNone(result)


class TestMessageRepositoryListBySession(unittest.TestCase):
    """Test MessageRepository.list_by_session method."""

    def test_list_by_session(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_messages = [MagicMock(), MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_offset = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.offset.return_value = mock_offset
        mock_offset.all.return_value = mock_messages

        result = MessageRepository.list_by_session(db, session_id)

        self.assertEqual(result, mock_messages)

    def test_list_by_session_with_pagination(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_offset = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.offset.return_value = mock_offset
        mock_offset.all.return_value = []

        MessageRepository.list_by_session(db, session_id, limit=50, offset=10)

        mock_order.limit.assert_called_once_with(50)
        mock_limit.offset.assert_called_once_with(10)


class TestMessageRepositoryListBySessionAfterId(unittest.TestCase):
    """Test MessageRepository.list_by_session_after_id method."""

    def test_list_without_after_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_messages = [MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_messages

        result = MessageRepository.list_by_session_after_id(
            db, session_id, after_id=0, limit=100
        )

        self.assertEqual(result, mock_messages)
        # Should not apply additional filter for after_id=0
        mock_query.filter.assert_called_once()

    def test_list_with_after_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_messages = [MagicMock()]
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter  # chain for second filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_messages

        result = MessageRepository.list_by_session_after_id(
            db, session_id, after_id=5, limit=100
        )

        self.assertEqual(result, mock_messages)
        # Should apply additional filter for after_id > 0
        self.assertEqual(mock_query.filter.call_count, 1)


class TestMessageRepositoryListIdsBySessionAfterId(unittest.TestCase):
    """Test MessageRepository.list_ids_by_session_after_id method."""

    def test_list_ids_without_after_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = [(1,), (2,), (3,)]

        result = MessageRepository.list_ids_by_session_after_id(
            db, session_id, after_id=0, limit=100
        )

        self.assertEqual(result, [1, 2, 3])

    def test_list_ids_with_after_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = [(10,)]

        result = MessageRepository.list_ids_by_session_after_id(
            db, session_id, after_id=5, limit=100
        )

        self.assertEqual(result, [10])


class TestMessageRepositoryCountBySession(unittest.TestCase):
    """Test MessageRepository.count_by_session method."""

    def test_count_by_session(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 42

        result = MessageRepository.count_by_session(db, session_id)

        self.assertEqual(result, 42)

    def test_count_by_session_zero(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 0

        result = MessageRepository.count_by_session(db, session_id)

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
