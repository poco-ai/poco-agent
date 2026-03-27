import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.repositories.run_repository import RunRepository


class TestRunRepositoryConstants(unittest.TestCase):
    """Test RunRepository constants."""

    def test_unfinished_statuses(self) -> None:
        self.assertEqual(
            RunRepository.UNFINISHED_STATUSES, ("queued", "claimed", "running")
        )

    def test_blocking_statuses(self) -> None:
        self.assertEqual(RunRepository.BLOCKING_STATUSES, ("claimed", "running"))

    def test_terminal_statuses(self) -> None:
        self.assertEqual(
            RunRepository.TERMINAL_STATUSES, ("completed", "failed", "canceled")
        )


class TestRunRepositoryCreate(unittest.TestCase):
    """Test RunRepository.create method."""

    def test_create_with_defaults(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        user_message_id = 1

        result = RunRepository.create(db, session_id, user_message_id)

        self.assertEqual(result.session_id, session_id)
        self.assertEqual(result.user_message_id, user_message_id)
        self.assertEqual(result.status, "queued")
        self.assertEqual(result.permission_mode, "default")
        self.assertEqual(result.schedule_mode, "immediate")
        self.assertEqual(result.progress, 0)
        self.assertEqual(result.attempts, 0)
        db.add.assert_called_once()

    def test_create_with_permission_mode(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        result = RunRepository.create(
            db, session_id, 1, permission_mode="bypassPermissions"
        )

        self.assertEqual(result.permission_mode, "bypassPermissions")

    def test_create_with_schedule_mode(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        result = RunRepository.create(db, session_id, 1, schedule_mode="nightly")

        self.assertEqual(result.schedule_mode, "nightly")

    def test_create_with_scheduled_at(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)

        result = RunRepository.create(db, session_id, 1, scheduled_at=scheduled_at)

        self.assertEqual(result.scheduled_at, scheduled_at)

    def test_create_with_config_snapshot(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        config = {"model": "test-model"}

        result = RunRepository.create(db, session_id, 1, config_snapshot=config)

        self.assertEqual(result.config_snapshot, config)


class TestRunRepositoryGetById(unittest.TestCase):
    """Test RunRepository.get_by_id method."""

    def test_get_by_id_found(self) -> None:
        db = MagicMock()
        run_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_run

        result = RunRepository.get_by_id(db, run_id)

        self.assertEqual(result, mock_run)

    def test_get_by_id_not_found(self) -> None:
        db = MagicMock()
        run_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        result = RunRepository.get_by_id(db, run_id)

        self.assertIsNone(result)


class TestRunRepositoryGetLatestBySession(unittest.TestCase):
    """Test RunRepository.get_latest_by_session method."""

    def test_get_latest_by_session_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.first.return_value = mock_run

        result = RunRepository.get_latest_by_session(db, session_id)

        self.assertEqual(result, mock_run)

    def test_get_latest_by_session_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.first.return_value = None

        result = RunRepository.get_latest_by_session(db, session_id)

        self.assertIsNone(result)


class TestRunRepositoryGetUnfinishedBySession(unittest.TestCase):
    """Test RunRepository.get_unfinished_by_session method."""

    def test_get_unfinished_by_session_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_order
        mock_order.order_by.return_value = MagicMock()
        MagicMock().first.return_value = mock_run

        # Set up the chain properly
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run

        result = RunRepository.get_unfinished_by_session(db, session_id)

        self.assertEqual(result, mock_run)

    def test_get_unfinished_by_session_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = RunRepository.get_unfinished_by_session(db, session_id)

        self.assertIsNone(result)


class TestRunRepositoryGetLatestTerminalBySession(unittest.TestCase):
    """Test RunRepository.get_latest_terminal_by_session method."""

    def test_get_latest_terminal_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run

        result = RunRepository.get_latest_terminal_by_session(db, session_id)

        self.assertEqual(result, mock_run)

    def test_get_latest_terminal_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = RunRepository.get_latest_terminal_by_session(db, session_id)

        self.assertIsNone(result)


class TestRunRepositoryGetBlockingBySession(unittest.TestCase):
    """Test RunRepository.get_blocking_by_session method."""

    def test_get_blocking_by_session_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run

        result = RunRepository.get_blocking_by_session(db, session_id)

        self.assertEqual(result, mock_run)

    def test_get_blocking_by_session_not_found(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = RunRepository.get_blocking_by_session(db, session_id)

        self.assertIsNone(result)

    def test_get_blocking_by_session_with_now(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = RunRepository.get_blocking_by_session(db, session_id, now=now)

        self.assertIsNone(result)


class TestRunRepositoryGetLatestActiveBySession(unittest.TestCase):
    """Test RunRepository.get_latest_active_by_session method."""

    def test_get_latest_active_delegates_to_get_blocking(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run

        result = RunRepository.get_latest_active_by_session(db, session_id)

        self.assertEqual(result, mock_run)


class TestRunRepositoryListBySession(unittest.TestCase):
    """Test RunRepository.list_by_session method."""

    def test_list_by_session(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_runs = [MagicMock(), MagicMock()]
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_runs

        result = RunRepository.list_by_session(db, session_id)

        self.assertEqual(result, mock_runs)

    def test_list_by_session_with_pagination(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        RunRepository.list_by_session(db, session_id, limit=50, offset=10)

        # Verify the chain was called correctly
        mock_query.filter.assert_called_once()


class TestRunRepositoryListBySessionAndUserMessageIds(unittest.TestCase):
    """Test RunRepository.list_by_session_and_user_message_ids method."""

    def test_list_with_empty_ids(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        result = RunRepository.list_by_session_and_user_message_ids(db, session_id, [])

        self.assertEqual(result, [])

    def test_list_with_ids(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        message_ids = [1, 2, 3]
        mock_runs = [MagicMock()]
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_runs

        result = RunRepository.list_by_session_and_user_message_ids(
            db, session_id, message_ids
        )

        self.assertEqual(result, mock_runs)


class TestRunRepositoryListByScheduledTask(unittest.TestCase):
    """Test RunRepository.list_by_scheduled_task method."""

    def test_list_by_scheduled_task(self) -> None:
        db = MagicMock()
        scheduled_task_id = uuid.uuid4()
        mock_runs = [MagicMock()]
        mock_query = MagicMock()

        db.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_runs

        result = RunRepository.list_by_scheduled_task(db, scheduled_task_id)

        self.assertEqual(result, mock_runs)


class TestRunRepositoryReleaseExpiredClaims(unittest.TestCase):
    """Test RunRepository.release_expired_claims method."""

    def test_release_expired_claims(self) -> None:
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result

        db.connection.return_value = mock_connection

        result = RunRepository.release_expired_claims(db)

        self.assertEqual(result, 5)
        mock_connection.execute.assert_called_once()

    def test_release_expired_claims_none(self) -> None:
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result

        db.connection.return_value = mock_connection

        result = RunRepository.release_expired_claims(db)

        self.assertEqual(result, 0)


class TestRunRepositoryClaimNext(unittest.TestCase):
    """Test RunRepository.claim_next method."""

    def test_claim_next_no_run_available(self) -> None:
        db = MagicMock()
        worker_id = "worker-1"

        # Mock release_expired_claims
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        db.connection.return_value = mock_connection

        # Mock execute for select
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_execute_result

        result = RunRepository.claim_next(db, worker_id)

        self.assertIsNone(result)

    def test_claim_next_with_lease_seconds_zero_or_negative(self) -> None:
        db = MagicMock()
        worker_id = "worker-1"

        # Mock release_expired_claims
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        db.connection.return_value = mock_connection

        # Mock execute for select
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_execute_result

        # Test with 0
        RunRepository.claim_next(db, worker_id, lease_seconds=0)
        # Should default to 30 seconds

        # Test with negative
        RunRepository.claim_next(db, worker_id, lease_seconds=-5)
        # Should default to 30 seconds

    def test_claim_next_with_schedule_modes(self) -> None:
        db = MagicMock()
        worker_id = "worker-1"

        # Mock release_expired_claims
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        db.connection.return_value = mock_connection

        # Mock execute for select
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        db.execute.return_value = mock_execute_result

        result = RunRepository.claim_next(
            db, worker_id, schedule_modes=["immediate", "nightly"]
        )

        self.assertIsNone(result)

    def test_claim_next_success(self) -> None:
        db = MagicMock()
        worker_id = "worker-1"

        # Mock release_expired_claims
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        db.connection.return_value = mock_connection

        # Mock run that gets claimed
        mock_run = MagicMock()
        mock_run.status = "queued"
        mock_run.claimed_by = None
        mock_run.lease_expires_at = None

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = mock_run
        db.execute.return_value = mock_execute_result

        result = RunRepository.claim_next(db, worker_id, lease_seconds=60)

        self.assertEqual(result, mock_run)
        self.assertEqual(mock_run.status, "claimed")
        self.assertEqual(mock_run.claimed_by, worker_id)
        self.assertIsNotNone(mock_run.lease_expires_at)


if __name__ == "__main__":
    unittest.main()
