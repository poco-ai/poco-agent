import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.user_input_request import (
    UserInputAnswerRequest,
    UserInputRequestCreateRequest,
    UserInputRequestResponse,
)
from app.services.user_input_request_service import (
    UserInputRequestService,
)


class TestUserInputRequestServiceCreateRequest(unittest.TestCase):
    """Test UserInputRequestService.create_request."""

    def setUp(self) -> None:
        self.service = UserInputRequestService()
        self.db = MagicMock()

    @patch("app.services.user_input_request_service.SessionRepository")
    def test_session_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        request = UserInputRequestCreateRequest(
            session_id=uuid.uuid4(),
            tool_name="ask",
            tool_input={"question": "Continue?"},
        )

        with self.assertRaises(AppException) as ctx:
            self.service.create_request(self.db, request)

        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    @patch("app.services.user_input_request_service.SessionRepository")
    def test_create_with_default_expiry(
        self, mock_session_repo: MagicMock, mock_request_repo: MagicMock
    ) -> None:
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        mock_session_repo.get_by_id.return_value = mock_session

        # Create a properly configured entry that will be returned after refresh
        mock_entry = MagicMock()
        mock_entry.id = uuid.uuid4()
        mock_entry.session_id = mock_session.id
        mock_entry.tool_name = "ask"
        mock_entry.tool_input = {"question": "Continue?"}
        mock_entry.status = "pending"
        mock_entry.expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        mock_entry.answers = None
        mock_entry.answered_at = None
        mock_entry.created_at = datetime.now(timezone.utc)
        mock_entry.updated_at = datetime.now(timezone.utc)

        # Make db.refresh update the entry
        def refresh_side_effect(entry):
            entry.id = mock_entry.id
            entry.created_at = mock_entry.created_at
            entry.updated_at = mock_entry.updated_at
            entry.status = mock_entry.status
            entry.expires_at = mock_entry.expires_at
            entry.answers = mock_entry.answers
            entry.answered_at = mock_entry.answered_at

        self.db.refresh = MagicMock(side_effect=refresh_side_effect)

        request = UserInputRequestCreateRequest(
            session_id=mock_session.id,
            tool_name="ask",
            tool_input={"question": "Continue?"},
        )

        with patch.object(self.service, "_enqueue_created_event"):
            result = self.service.create_request(self.db, request)

        mock_request_repo.create.assert_called_once()
        self.assertIsInstance(result, UserInputRequestResponse)


class TestUserInputRequestServiceGetRequest(unittest.TestCase):
    """Test UserInputRequestService.get_request."""

    def setUp(self) -> None:
        self.service = UserInputRequestService()
        self.db = MagicMock()

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_request_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.get_request(self.db, "request-123")

        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)

    def _make_entry(self, **kwargs) -> MagicMock:
        """Create a properly configured mock UserInputRequest."""
        mock = MagicMock()
        mock.id = kwargs.get("id", uuid.uuid4())
        mock.status = kwargs.get("status", "pending")
        mock.expires_at = kwargs.get(
            "expires_at", datetime.now(timezone.utc) + timedelta(hours=1)
        )
        mock.tool_name = kwargs.get("tool_name", "ask")
        mock.tool_input = kwargs.get("tool_input", {})
        mock.session_id = kwargs.get("session_id", uuid.uuid4())
        mock.answers = kwargs.get("answers", None)
        mock.answered_at = kwargs.get("answered_at", None)
        return mock

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_get_pending_request(self, mock_repo: MagicMock) -> None:
        mock_entry = self._make_entry()
        mock_repo.get_by_id.return_value = mock_entry

        result = self.service.get_request(self.db, str(mock_entry.id))

        self.assertIsInstance(result, UserInputRequestResponse)

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_expire_pending_request(self, mock_repo: MagicMock) -> None:
        mock_entry = self._make_entry(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        mock_repo.get_by_id.return_value = mock_entry

        self.service.get_request(self.db, str(mock_entry.id), allow_expire=True)

        self.assertEqual(mock_entry.status, "expired")


class TestUserInputRequestServiceAnswerRequest(unittest.TestCase):
    """Test UserInputRequestService.answer_request."""

    def setUp(self) -> None:
        self.service = UserInputRequestService()
        self.db = MagicMock()
        self.user_id = "user-123"

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_request_not_found(self, mock_repo: MagicMock) -> None:
        mock_repo.get_by_id.return_value = None

        with self.assertRaises(AppException) as ctx:
            self.service.answer_request(
                self.db,
                self.user_id,
                "request-123",
                UserInputAnswerRequest(answers={"response": "yes"}),
            )

        self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)

    @patch("app.services.user_input_request_service.SessionRepository")
    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_wrong_user(
        self, mock_request_repo: MagicMock, mock_session_repo: MagicMock
    ) -> None:
        mock_entry = MagicMock()
        mock_entry.session_id = uuid.uuid4()
        mock_request_repo.get_by_id.return_value = mock_entry

        mock_session = MagicMock()
        mock_session.user_id = "other-user"
        mock_session_repo.get_by_id.return_value = mock_session

        with self.assertRaises(AppException) as ctx:
            self.service.answer_request(
                self.db,
                self.user_id,
                "request-123",
                UserInputAnswerRequest(answers={"response": "yes"}),
            )

        self.assertEqual(ctx.exception.error_code, ErrorCode.FORBIDDEN)

    @patch("app.services.user_input_request_service.SessionRepository")
    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_not_pending(
        self, mock_request_repo: MagicMock, mock_session_repo: MagicMock
    ) -> None:
        mock_entry = MagicMock()
        mock_entry.session_id = uuid.uuid4()
        mock_entry.status = "answered"
        mock_request_repo.get_by_id.return_value = mock_entry

        mock_session = MagicMock()
        mock_session.user_id = self.user_id
        mock_session_repo.get_by_id.return_value = mock_session

        with self.assertRaises(AppException) as ctx:
            self.service.answer_request(
                self.db,
                self.user_id,
                "request-123",
                UserInputAnswerRequest(answers={"response": "yes"}),
            )

        self.assertEqual(ctx.exception.error_code, ErrorCode.BAD_REQUEST)


class TestUserInputRequestServiceListPending(unittest.TestCase):
    """Test UserInputRequestService.list_pending_for_user."""

    def setUp(self) -> None:
        self.service = UserInputRequestService()
        self.db = MagicMock()

    def _make_entry(self, **kwargs) -> MagicMock:
        """Create a properly configured mock UserInputRequest."""
        mock = MagicMock()
        mock.id = kwargs.get("id", uuid.uuid4())
        mock.status = kwargs.get("status", "pending")
        mock.expires_at = kwargs.get(
            "expires_at", datetime.now(timezone.utc) + timedelta(hours=1)
        )
        mock.tool_name = kwargs.get("tool_name", "ask")
        mock.tool_input = kwargs.get("tool_input", {})
        mock.session_id = kwargs.get("session_id", uuid.uuid4())
        mock.answers = kwargs.get("answers", None)
        mock.answered_at = kwargs.get("answered_at", None)
        return mock

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_list_pending(self, mock_repo: MagicMock) -> None:
        mock_entry = self._make_entry()
        mock_repo.list_pending_by_user.return_value = [mock_entry]

        result = self.service.list_pending_for_user(self.db, "user-123")

        self.assertEqual(len(result), 1)

    @patch("app.services.user_input_request_service.UserInputRequestRepository")
    def test_list_pending_with_session_id(self, mock_repo: MagicMock) -> None:
        session_id = uuid.uuid4()
        mock_repo.list_pending_by_user.return_value = []

        result = self.service.list_pending_for_user(
            self.db, "user-123", session_id=session_id
        )

        mock_repo.list_pending_by_user.assert_called_once()
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
