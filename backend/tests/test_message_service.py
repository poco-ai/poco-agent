import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.input_file import InputFile
from app.services.message_service import MessageService


def create_mock_message(
    message_id: int = 1,
    session_id: uuid.UUID | None = None,
    role: str = "user",
    content: dict | None = None,
    text_preview: str = "Hello",
) -> MagicMock:
    """Create a properly configured mock message with required datetime fields."""
    mock = MagicMock()
    mock.id = message_id
    mock.session_id = session_id or uuid.uuid4()
    mock.role = role
    mock.content = content or {}
    mock.text_preview = text_preview
    mock.created_at = datetime.now(timezone.utc)
    return mock


class TestMessageServiceCollectMessageAttachments(unittest.TestCase):
    """Test _collect_message_attachments static method."""

    def test_empty_runs_list(self) -> None:
        result = MessageService._collect_message_attachments([])
        self.assertEqual(result, {})

    def test_run_without_config_snapshot(self) -> None:
        run = MagicMock()
        run.config_snapshot = None
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertEqual(result, {})

    def test_run_with_non_dict_config_snapshot(self) -> None:
        run = MagicMock()
        run.config_snapshot = "not a dict"
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertEqual(result, {})

    def test_run_without_input_files(self) -> None:
        run = MagicMock()
        run.config_snapshot = {"other_key": "value"}
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertEqual(result, {})

    def test_run_with_empty_input_files(self) -> None:
        run = MagicMock()
        run.config_snapshot = {"input_files": []}
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertEqual(result, {})

    def test_run_with_non_list_input_files(self) -> None:
        run = MagicMock()
        run.config_snapshot = {"input_files": "not a list"}
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertEqual(result, {})

    def test_run_with_valid_input_files(self) -> None:
        run = MagicMock()
        run.config_snapshot = {
            "input_files": [
                {
                    "source": "file1.txt",
                    "content_type": "text/plain",
                    "name": "file1.txt",
                }
            ]
        }
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertIn(1, result)
        self.assertEqual(len(result[1]), 1)

    def test_run_with_invalid_input_file_item(self) -> None:
        run = MagicMock()
        run.config_snapshot = {
            "input_files": [
                "not a dict",
                {
                    "source": "file1.txt",
                    "content_type": "text/plain",
                    "name": "file1.txt",
                },
            ]
        }
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        self.assertIn(1, result)
        self.assertEqual(len(result[1]), 1)

    def test_run_with_malformed_input_file(self) -> None:
        run = MagicMock()
        run.config_snapshot = {
            "input_files": [
                {"invalid": "structure"},  # Missing required fields
            ]
        }
        run.user_message_id = 1

        result = MessageService._collect_message_attachments([run])
        # Should skip invalid items
        self.assertEqual(result, {})

    def test_multiple_runs(self) -> None:
        run1 = MagicMock()
        run1.config_snapshot = {
            "input_files": [
                {
                    "source": "file1.txt",
                    "content_type": "text/plain",
                    "name": "file1.txt",
                }
            ]
        }
        run1.user_message_id = 1

        run2 = MagicMock()
        run2.config_snapshot = {
            "input_files": [
                {
                    "source": "file2.txt",
                    "content_type": "text/plain",
                    "name": "file2.txt",
                }
            ]
        }
        run2.user_message_id = 2

        result = MessageService._collect_message_attachments([run1, run2])
        self.assertIn(1, result)
        self.assertIn(2, result)


class TestMessageServiceToInputFilesWithUrls(unittest.TestCase):
    """Test _to_input_files_with_urls static method."""

    def test_empty_attachments(self) -> None:
        storage = MagicMock()
        result = MessageService._to_input_files_with_urls(
            [], user_id="user-123", storage_service=storage
        )
        self.assertEqual(result, [])

    def test_attachment_without_source(self) -> None:
        storage = MagicMock()
        file = InputFile(source="", content_type="text/plain", name="file.txt")
        result = MessageService._to_input_files_with_urls(
            [file], user_id="user-123", storage_service=storage
        )
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].url)

    def test_attachment_with_wrong_prefix(self) -> None:
        storage = MagicMock()
        file = InputFile(
            source="other/prefix/file.txt",
            content_type="text/plain",
            name="file.txt",
        )
        result = MessageService._to_input_files_with_urls(
            [file], user_id="user-123", storage_service=storage
        )
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].url)

    def test_attachment_with_valid_prefix(self) -> None:
        storage = MagicMock()
        storage.presign_get.return_value = "https://presigned.url"

        file = InputFile(
            source="attachments/user-123/file.txt",
            content_type="text/plain",
            name="file.txt",
        )
        result = MessageService._to_input_files_with_urls(
            [file], user_id="user-123", storage_service=storage
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, "https://presigned.url")
        storage.presign_get.assert_called_once()

    def test_attachment_presign_raises_exception(self) -> None:
        storage = MagicMock()
        storage.presign_get.side_effect = Exception("S3 error")

        file = InputFile(
            source="attachments/user-123/file.txt",
            content_type="text/plain",
            name="file.txt",
        )
        result = MessageService._to_input_files_with_urls(
            [file], user_id="user-123", storage_service=storage
        )
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].url)


class TestMessageServiceGetMessages(unittest.TestCase):
    """Test get_messages method."""

    def test_get_messages(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_messages = [MagicMock(), MagicMock()]

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.list_by_session.return_value = mock_messages
            service = MessageService()
            result = service.get_messages(db, session_id)

            self.assertEqual(result, mock_messages)
            mock_repo.list_by_session.assert_called_once_with(db, session_id)


class TestMessageServiceGetMessage(unittest.TestCase):
    """Test get_message method."""

    def test_get_message_found(self) -> None:
        db = MagicMock()
        message_id = 1
        mock_message = MagicMock()

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.get_by_id.return_value = mock_message
            service = MessageService()
            result = service.get_message(db, message_id)

            self.assertEqual(result, mock_message)

    def test_get_message_not_found(self) -> None:
        db = MagicMock()
        message_id = 1

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.get_by_id.return_value = None
            service = MessageService()
            with self.assertRaises(AppException) as ctx:
                service.get_message(db, message_id)
            self.assertEqual(ctx.exception.error_code, ErrorCode.NOT_FOUND)


class TestMessageServiceGetMessagesDelta(unittest.TestCase):
    """Test get_messages_delta method."""

    def test_get_messages_delta_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.list_by_session_after_id.return_value = []
            service = MessageService()
            result = service.get_messages_delta(db, session_id)

            self.assertEqual(result.items, [])
            self.assertFalse(result.has_more)

    def test_get_messages_delta_with_messages(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        mock_message = create_mock_message(message_id=1, session_id=session_id)

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.list_by_session_after_id.return_value = [mock_message]
            service = MessageService()
            result = service.get_messages_delta(db, session_id)

            self.assertEqual(len(result.items), 1)
            self.assertFalse(result.has_more)

    def test_get_messages_delta_has_more(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        mock_messages = [
            create_mock_message(message_id=i, session_id=session_id) for i in range(3)
        ]

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.list_by_session_after_id.return_value = mock_messages
            service = MessageService()
            # Request limit=2, but we get 3 messages, so has_more=True
            result = service.get_messages_delta(db, session_id, limit=2)

            self.assertTrue(result.has_more)
            self.assertEqual(len(result.items), 2)

    def test_get_messages_delta_with_after_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_repo:
            mock_repo.list_by_session_after_id.return_value = []
            service = MessageService()
            service.get_messages_delta(db, session_id, after_message_id=5, limit=10)

            mock_repo.list_by_session_after_id.assert_called_once()


class TestMessageServiceGetMessagesWithFilesDelta(unittest.TestCase):
    """Test get_messages_with_files_delta method."""

    def test_get_messages_with_files_delta_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository"):
                with patch("app.services.message_service.S3StorageService"):
                    mock_msg_repo.list_by_session_after_id.return_value = []
                    service = MessageService()
                    result = service.get_messages_with_files_delta(
                        db, session_id, user_id="user-123"
                    )

                    self.assertEqual(result.items, [])
                    self.assertFalse(result.has_more)

    def test_get_messages_with_files_delta_with_messages(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        mock_message = create_mock_message(message_id=1, session_id=session_id)

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository") as mock_run_repo:
                with patch("app.services.message_service.S3StorageService"):
                    mock_msg_repo.list_by_session_after_id.return_value = [mock_message]
                    mock_run_repo.list_by_session_and_user_message_ids.return_value = []

                    service = MessageService()
                    result = service.get_messages_with_files_delta(
                        db, session_id, user_id="user-123"
                    )

                    self.assertEqual(len(result.items), 1)


class TestMessageServiceGetMessageAttachmentsDelta(unittest.TestCase):
    """Test get_message_attachments_delta method."""

    def test_get_message_attachments_delta_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            mock_msg_repo.list_ids_by_session_after_id.return_value = []
            service = MessageService()
            result = service.get_message_attachments_delta(
                db, session_id, user_id="user-123"
            )

            self.assertEqual(result.items, [])
            self.assertFalse(result.has_more)

    def test_get_message_attachments_delta_with_messages(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository") as mock_run_repo:
                with patch("app.services.message_service.S3StorageService"):
                    mock_msg_repo.list_ids_by_session_after_id.return_value = [1, 2]
                    mock_run_repo.list_by_session_and_user_message_ids.return_value = []

                    service = MessageService()
                    result = service.get_message_attachments_delta(
                        db, session_id, user_id="user-123"
                    )

                    # No attachments since runs return empty
                    self.assertEqual(result.items, [])
                    self.assertFalse(result.has_more)

    def test_get_message_attachments_delta_has_more(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.S3StorageService"):
                mock_msg_repo.list_ids_by_session_after_id.return_value = [1, 2, 3]

                service = MessageService()
                # Request limit=2, get 3 messages
                result = service.get_message_attachments_delta(
                    db, session_id, user_id="user-123", limit=2
                )

                self.assertTrue(result.has_more)


class TestMessageServiceGetMessageAttachments(unittest.TestCase):
    """Test get_message_attachments method."""

    def test_get_message_attachments_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch.object(
            MessageService, "_build_message_id_to_attachments", return_value={}
        ):
            with patch("app.services.message_service.S3StorageService"):
                service = MessageService()
                result = service.get_message_attachments(
                    db, session_id, user_id="user-123"
                )

                self.assertEqual(result, [])

    def test_get_message_attachments_with_data(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        file = InputFile(
            source="attachments/user-123/file.txt",
            content_type="text/plain",
            name="file.txt",
        )

        with patch.object(
            MessageService, "_build_message_id_to_attachments", return_value={1: [file]}
        ):
            with patch(
                "app.services.message_service.S3StorageService"
            ) as mock_storage_cls:
                mock_storage = MagicMock()
                mock_storage.presign_get.return_value = "https://presigned.url"
                mock_storage_cls.return_value = mock_storage

                service = MessageService()
                result = service.get_message_attachments(
                    db, session_id, user_id="user-123"
                )

                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].message_id, 1)


class TestMessageServiceBuildMessageIdToAttachments(unittest.TestCase):
    """Test _build_message_id_to_attachments method."""

    def test_build_message_id_to_attachments(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_run.config_snapshot = {
            "input_files": [
                {"source": "file.txt", "content_type": "text/plain", "name": "file.txt"}
            ]
        }
        mock_run.user_message_id = 1

        with patch("app.services.message_service.RunRepository") as mock_repo:
            mock_repo.list_by_session.return_value = [mock_run]
            service = MessageService()
            result = service._build_message_id_to_attachments(db, session_id)

            self.assertIn(1, result)


class TestMessageServiceGetMessagesWithFiles(unittest.TestCase):
    """Test get_messages_with_files method."""

    def test_get_messages_with_files_empty(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository") as mock_run_repo:
                with patch("app.services.message_service.S3StorageService"):
                    mock_msg_repo.list_by_session.return_value = []
                    mock_run_repo.list_by_session.return_value = []

                    service = MessageService()
                    result = service.get_messages_with_files(
                        db, session_id, user_id="user-123"
                    )

                    self.assertEqual(result, [])

    def test_get_messages_with_files_with_messages(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        mock_message = create_mock_message(message_id=1, session_id=session_id)
        mock_run = MagicMock()
        mock_run.config_snapshot = {
            "input_files": [
                {
                    "source": "attachments/user-123/file.txt",
                    "content_type": "text/plain",
                    "name": "file.txt",
                }
            ]
        }
        mock_run.user_message_id = 1

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository") as mock_run_repo:
                with patch(
                    "app.services.message_service.S3StorageService"
                ) as mock_storage_cls:
                    mock_storage = MagicMock()
                    mock_storage.presign_get.return_value = "https://presigned.url"
                    mock_storage_cls.return_value = mock_storage

                    mock_msg_repo.list_by_session.return_value = [mock_message]
                    mock_run_repo.list_by_session.return_value = [mock_run]

                    service = MessageService()
                    result = service.get_messages_with_files(
                        db, session_id, user_id="user-123"
                    )

                    self.assertEqual(len(result), 1)


class TestMessageServiceGetMessageAttachmentsDeltaWithAttachments(unittest.TestCase):
    """Test get_message_attachments_delta with actual attachments."""

    def test_get_message_attachments_delta_with_attachments(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()

        mock_run = MagicMock()
        mock_run.config_snapshot = {
            "input_files": [
                {
                    "source": "attachments/user-123/file.txt",
                    "content_type": "text/plain",
                    "name": "file.txt",
                }
            ]
        }
        mock_run.user_message_id = 1

        with patch("app.services.message_service.MessageRepository") as mock_msg_repo:
            with patch("app.services.message_service.RunRepository") as mock_run_repo:
                with patch(
                    "app.services.message_service.S3StorageService"
                ) as mock_storage_cls:
                    mock_storage = MagicMock()
                    mock_storage.presign_get.return_value = "https://presigned.url"
                    mock_storage_cls.return_value = mock_storage

                    mock_msg_repo.list_ids_by_session_after_id.return_value = [1]
                    mock_run_repo.list_by_session_and_user_message_ids.return_value = [
                        mock_run
                    ]

                    service = MessageService()
                    result = service.get_message_attachments_delta(
                        db, session_id, user_id="user-123"
                    )

                    self.assertEqual(len(result.items), 1)
                    self.assertEqual(result.items[0].message_id, 1)


if __name__ == "__main__":
    unittest.main()
