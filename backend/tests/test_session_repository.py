import unittest
import uuid
from unittest.mock import MagicMock

from app.models.agent_session import AgentSession
from app.repositories.session_repository import SessionRepository


class TestSessionRepositoryCreate(unittest.TestCase):
    """Test SessionRepository.create method."""

    def test_create_with_defaults(self) -> None:
        db = MagicMock()
        user_id = "user-123"

        result = SessionRepository.create(db, user_id)

        self.assertEqual(result.user_id, user_id)
        self.assertEqual(result.kind, "chat")
        self.assertEqual(result.status, "pending")
        self.assertIsNone(result.config_snapshot)
        self.assertIsNone(result.project_id)
        db.add.assert_called_once()

    def test_create_with_config(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        config = {"model": "test-model"}

        result = SessionRepository.create(db, user_id, config=config)

        self.assertEqual(result.config_snapshot, config)

    def test_create_with_project_id(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()

        result = SessionRepository.create(db, user_id, project_id=project_id)

        self.assertEqual(result.project_id, project_id)

    def test_create_with_kind(self) -> None:
        db = MagicMock()
        user_id = "user-123"

        result = SessionRepository.create(db, user_id, kind="task")

        self.assertEqual(result.kind, "task")


class TestSessionRepositoryGetById(unittest.TestCase):
    """Test SessionRepository.get_by_id method."""

    def test_get_by_id_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_session

        result = SessionRepository.get_by_id(db, session_id)

        self.assertEqual(result, mock_session)
        db.query.assert_called_once_with(AgentSession)

    def test_get_by_id_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = SessionRepository.get_by_id(db, session_id)

        self.assertIsNone(result)


class TestSessionRepositoryGetByIdForUpdate(unittest.TestCase):
    """Test SessionRepository.get_by_id_for_update method."""

    def test_get_by_id_for_update_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_for_update = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_for_update
        mock_for_update.first.return_value = mock_session

        result = SessionRepository.get_by_id_for_update(db, session_id)

        self.assertEqual(result, mock_session)
        mock_filter.with_for_update.assert_called_once()

    def test_get_by_id_for_update_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_for_update = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_for_update
        mock_for_update.first.return_value = None

        result = SessionRepository.get_by_id_for_update(db, session_id)

        self.assertIsNone(result)


class TestSessionRepositoryGetBySdkSessionId(unittest.TestCase):
    """Test SessionRepository.get_by_sdk_session_id method."""

    def test_get_by_sdk_session_id_found(self) -> None:
        db = MagicMock()
        sdk_session_id = "sdk-123"
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_session

        result = SessionRepository.get_by_sdk_session_id(db, sdk_session_id)

        self.assertEqual(result, mock_session)

    def test_get_by_sdk_session_id_not_found(self) -> None:
        db = MagicMock()
        sdk_session_id = "sdk-123"
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = SessionRepository.get_by_sdk_session_id(db, sdk_session_id)

        self.assertIsNone(result)


class TestSessionRepositoryListByUser(unittest.TestCase):
    """Test SessionRepository.list_by_user method."""

    def test_list_by_user_basic(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_sessions = [MagicMock(), MagicMock()]
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
        mock_offset.all.return_value = mock_sessions

        result = SessionRepository.list_by_user(db, user_id)

        self.assertEqual(result, mock_sessions)

    def test_list_by_user_with_kind(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = MagicMock()
        MagicMock().limit.return_value = MagicMock()
        MagicMock().offset.return_value = MagicMock()

        SessionRepository.list_by_user(db, user_id, kind="task")

        # Verify filter was called twice (user_id + kind)
        self.assertEqual(mock_filter.filter.call_count, 1)

    def test_list_by_user_with_project_id(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        project_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = MagicMock()

        SessionRepository.list_by_user(db, user_id, project_id=project_id)

        # Verify filter was called for project_id
        self.assertEqual(mock_filter.filter.call_count, 1)

    def test_list_by_user_with_limit_offset(self) -> None:
        db = MagicMock()
        user_id = "user-123"
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

        SessionRepository.list_by_user(db, user_id, limit=50, offset=10)

        mock_order.limit.assert_called_once_with(50)
        mock_limit.offset.assert_called_once_with(10)


class TestSessionRepositoryListAll(unittest.TestCase):
    """Test SessionRepository.list_all method."""

    def test_list_all_basic(self) -> None:
        db = MagicMock()
        mock_sessions = [MagicMock(), MagicMock()]
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
        mock_offset.all.return_value = mock_sessions

        result = SessionRepository.list_all(db)

        self.assertEqual(result, mock_sessions)

    def test_list_all_with_kind(self) -> None:
        db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = MagicMock()

        SessionRepository.list_all(db, kind="chat")

        self.assertEqual(mock_filter.filter.call_count, 1)

    def test_list_all_with_project_id(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = MagicMock()

        SessionRepository.list_all(db, project_id=project_id)

        self.assertEqual(mock_filter.filter.call_count, 1)


class TestSessionRepositoryCountByUser(unittest.TestCase):
    """Test SessionRepository.count_by_user method."""

    def test_count_by_user(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 5

        result = SessionRepository.count_by_user(db, user_id)

        self.assertEqual(result, 5)

    def test_count_by_user_zero(self) -> None:
        db = MagicMock()
        user_id = "user-123"
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 0

        result = SessionRepository.count_by_user(db, user_id)

        self.assertEqual(result, 0)


class TestSessionRepositoryClearProjectId(unittest.TestCase):
    """Test SessionRepository.clear_project_id method."""

    def test_clear_project_id(self) -> None:
        db = MagicMock()
        project_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter

        SessionRepository.clear_project_id(db, project_id)

        db.query.assert_called_once_with(AgentSession)
        mock_filter.update.assert_called_once()
        # Check the update was called with correct params
        call_args = mock_filter.update.call_args
        self.assertEqual(call_args.args[0], {AgentSession.project_id: None})


if __name__ == "__main__":
    unittest.main()
