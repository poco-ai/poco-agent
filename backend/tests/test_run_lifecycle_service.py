import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.services.run_lifecycle_service import RunLifecycleService


class TestRunLifecycleServiceSyncScheduledTask(unittest.TestCase):
    """Test RunLifecycleService._sync_scheduled_task_last_status."""

    def setUp(self) -> None:
        self.service = RunLifecycleService()
        self.db = MagicMock()

    def test_no_scheduled_task_id(self) -> None:
        db_run = MagicMock()
        db_run.scheduled_task_id = None

        self.service._sync_scheduled_task_last_status(self.db, db_run)

    @patch("app.services.run_lifecycle_service.ScheduledTaskRepository")
    def test_task_not_found(self, mock_repo: MagicMock) -> None:
        db_run = MagicMock()
        db_run.scheduled_task_id = uuid.uuid4()
        mock_repo.get_by_id.return_value = None

        self.service._sync_scheduled_task_last_status(self.db, db_run)

        mock_repo.get_by_id.assert_called_once()

    @patch("app.services.run_lifecycle_service.ScheduledTaskRepository")
    def test_different_last_run_id(self, mock_repo: MagicMock) -> None:
        db_run = MagicMock()
        db_run.scheduled_task_id = uuid.uuid4()
        db_run.id = 123
        db_run.status = "completed"

        db_task = MagicMock()
        db_task.last_run_id = 456
        mock_repo.get_by_id.return_value = db_task

        self.service._sync_scheduled_task_last_status(self.db, db_run)

        self.assertEqual(db_task.last_run_id, 456)

    @patch("app.services.run_lifecycle_service.ScheduledTaskRepository")
    def test_updates_on_matching_last_run_id(self, mock_repo: MagicMock) -> None:
        run_id = 123
        db_run = MagicMock()
        db_run.scheduled_task_id = uuid.uuid4()
        db_run.id = run_id
        db_run.status = "completed"

        db_task = MagicMock()
        db_task.last_run_id = run_id
        mock_repo.get_by_id.return_value = db_task

        self.service._sync_scheduled_task_last_status(self.db, db_run)

        self.assertEqual(db_task.last_run_status, "completed")


class TestRunLifecycleServiceMarkRunning(unittest.TestCase):
    """Test RunLifecycleService.mark_running."""

    def setUp(self) -> None:
        self.service = RunLifecycleService()
        self.db = MagicMock()

    @patch("app.services.run_lifecycle_service.SessionRepository")
    def test_session_not_found(self, mock_repo: MagicMock) -> None:
        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        mock_repo.get_by_id_for_update.return_value = None

        result = self.service.mark_running(self.db, db_run)

        self.assertIsNone(result)

    @patch("app.services.run_lifecycle_service.SessionRepository")
    @patch("app.services.run_lifecycle_service.session_queue_service")
    def test_terminal_status_unchanged(
        self, mock_queue: MagicMock, mock_repo: MagicMock
    ) -> None:
        db_session = MagicMock()
        mock_repo.get_by_id_for_update.return_value = db_session

        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        db_run.status = "completed"

        result = self.service.mark_running(self.db, db_run)

        self.assertEqual(result, db_session)

    @patch("app.services.run_lifecycle_service.SessionRepository")
    @patch("app.services.run_lifecycle_service.session_queue_service")
    def test_queued_to_running(
        self, mock_queue: MagicMock, mock_repo: MagicMock
    ) -> None:
        db_session = MagicMock()
        db_session.status = "pending"
        mock_repo.get_by_id_for_update.return_value = db_session

        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        db_run.status = "queued"
        db_run.started_at = None

        self.service.mark_running(self.db, db_run)

        self.assertEqual(db_run.status, "running")
        self.assertIsNotNone(db_run.started_at)
        mock_queue.clear_execution_state.assert_called_once()


class TestRunLifecycleServiceFinalizeTerminal(unittest.TestCase):
    """Test RunLifecycleService.finalize_terminal."""

    def setUp(self) -> None:
        self.service = RunLifecycleService()
        self.db = MagicMock()

    @patch("app.services.run_lifecycle_service.SessionRepository")
    def test_session_not_found(self, mock_repo: MagicMock) -> None:
        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        mock_repo.get_by_id_for_update.return_value = None

        result = self.service.finalize_terminal(self.db, db_run, status="completed")

        self.assertEqual(result, (None, None))

    @patch("app.services.run_lifecycle_service.SessionRepository")
    @patch("app.services.run_lifecycle_service.session_queue_service")
    def test_completed_status(
        self, mock_queue: MagicMock, mock_repo: MagicMock
    ) -> None:
        db_session = MagicMock()
        mock_repo.get_by_id_for_update.return_value = db_session

        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        db_run.status = "running"
        db_run.finished_at = None

        mock_queue.promote_next_if_available.return_value = None

        self.service.finalize_terminal(self.db, db_run, status="completed")

        self.assertEqual(db_run.status, "completed")
        self.assertEqual(db_run.progress, 100)
        self.assertIsNotNone(db_run.finished_at)

    @patch("app.services.run_lifecycle_service.SessionRepository")
    @patch("app.services.run_lifecycle_service.session_queue_service")
    def test_failed_status(self, mock_queue: MagicMock, mock_repo: MagicMock) -> None:
        db_session = MagicMock()
        mock_repo.get_by_id_for_update.return_value = db_session

        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        db_run.status = "running"
        db_run.finished_at = None

        self.service.finalize_terminal(
            self.db, db_run, status="failed", error_message="Error message"
        )

        self.assertEqual(db_run.status, "failed")
        self.assertEqual(db_run.last_error, "Error message")
        mock_queue.pause_active_items.assert_called_once()

    @patch("app.services.run_lifecycle_service.SessionRepository")
    @patch("app.services.run_lifecycle_service.session_queue_service")
    def test_canceled_status(self, mock_queue: MagicMock, mock_repo: MagicMock) -> None:
        db_session = MagicMock()
        mock_repo.get_by_id_for_update.return_value = db_session

        db_run = MagicMock()
        db_run.session_id = uuid.uuid4()
        db_run.status = "running"
        db_run.finished_at = None

        self.service.finalize_terminal(self.db, db_run, status="canceled")

        self.assertEqual(db_run.status, "canceled")
        mock_queue.cancel_active_items.assert_called_once()


if __name__ == "__main__":
    unittest.main()
