import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.schemas.callback import AgentCallbackRequest, CallbackStatus
from app.services.callback_service import CallbackService


def create_mock_db_session(
    session_id: uuid.UUID | None = None,
    status: str = "running",
    title: str = "Test Session",
    sdk_session_id: str = "sdk-123",
    workspace_export_status: str | None = None,
    workspace_files_prefix: str | None = None,
    workspace_manifest_key: str | None = None,
    workspace_archive_key: str | None = None,
) -> MagicMock:
    """Helper to create a properly configured mock AgentSession."""
    mock = MagicMock()
    mock.id = session_id or uuid.uuid4()
    mock.status = status
    mock.title = title
    mock.sdk_session_id = sdk_session_id
    mock.workspace_export_status = workspace_export_status
    mock.workspace_files_prefix = workspace_files_prefix
    mock.workspace_manifest_key = workspace_manifest_key
    mock.workspace_archive_key = workspace_archive_key
    mock.state_patch = None
    return mock


def create_callback_request(
    session_id: str = "session-1",
    status: CallbackStatus = CallbackStatus.COMPLETED,
    **kwargs: object,
) -> AgentCallbackRequest:
    """Helper to create AgentCallbackRequest with required fields."""
    return AgentCallbackRequest(
        session_id=session_id,
        status=status,
        time=kwargs.pop("time", datetime.now(timezone.utc)),
        progress=kwargs.pop("progress", 0),
        **kwargs,  # type: ignore[arg-type]
    )


class TestCallbackServiceParseRunId(unittest.TestCase):
    """Test _parse_run_id method."""

    def test_none_input(self) -> None:
        service = CallbackService()
        result = service._parse_run_id(None)
        self.assertIsNone(result)

    def test_empty_string(self) -> None:
        service = CallbackService()
        result = service._parse_run_id("")
        self.assertIsNone(result)

    def test_invalid_uuid(self) -> None:
        service = CallbackService()
        result = service._parse_run_id("not-a-uuid")
        self.assertIsNone(result)

    def test_valid_uuid(self) -> None:
        service = CallbackService()
        test_uuid = uuid.uuid4()
        result = service._parse_run_id(str(test_uuid))
        self.assertEqual(result, test_uuid)

    def test_whitespace_string(self) -> None:
        service = CallbackService()
        result = service._parse_run_id("   ")
        self.assertIsNone(result)


class TestCallbackServiceIsFinalWorkspaceExport(unittest.TestCase):
    """Test _is_final_workspace_export method."""

    def test_none_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status=None)
        result = service._is_final_workspace_export(callback)
        self.assertFalse(result)

    def test_empty_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="")
        result = service._is_final_workspace_export(callback)
        self.assertFalse(result)

    def test_pending_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="pending")
        result = service._is_final_workspace_export(callback)
        self.assertFalse(result)

    def test_ready_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="ready")
        result = service._is_final_workspace_export(callback)
        self.assertTrue(result)

    def test_failed_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="failed")
        result = service._is_final_workspace_export(callback)
        self.assertTrue(result)

    def test_case_insensitive(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="READY")
        result = service._is_final_workspace_export(callback)
        self.assertTrue(result)


class TestCallbackServiceExtractSdkSessionIdFromMessage(unittest.TestCase):
    """Test _extract_sdk_session_id_from_message method."""

    def test_result_message_with_session_id(self) -> None:
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "session_id": "sdk-session-123",
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertEqual(result, "sdk-session-123")

    def test_result_message_without_session_id(self) -> None:
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertIsNone(result)

    def test_result_message_non_string_session_id(self) -> None:
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "session_id": 123,
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertIsNone(result)

    def test_system_message_init_with_nested_data(self) -> None:
        service = CallbackService()
        message = {
            "_type": "SystemMessage",
            "subtype": "init",
            "data": {
                "data": {
                    "session_id": "nested-session-456",
                }
            },
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertEqual(result, "nested-session-456")

    def test_system_message_init_with_direct_session_id(self) -> None:
        service = CallbackService()
        message = {
            "_type": "SystemMessage",
            "subtype": "init",
            "data": {
                "session_id": "direct-session-789",
            },
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertEqual(result, "direct-session-789")

    def test_system_message_non_init_subtype(self) -> None:
        service = CallbackService()
        message = {
            "_type": "SystemMessage",
            "subtype": "other",
            "data": {
                "session_id": "session-xxx",
            },
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertIsNone(result)

    def test_system_message_init_invalid_data(self) -> None:
        service = CallbackService()
        message = {
            "_type": "SystemMessage",
            "subtype": "init",
            "data": "not a dict",
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertIsNone(result)

    def test_unknown_message_type(self) -> None:
        service = CallbackService()
        message = {
            "_type": "UnknownMessage",
            "session_id": "session-xxx",
        }
        result = service._extract_sdk_session_id_from_message(message)
        self.assertIsNone(result)


class TestCallbackServiceExtractRoleFromMessage(unittest.TestCase):
    """Test _extract_role_from_message method."""

    def test_assistant_message(self) -> None:
        service = CallbackService()
        message = {"_type": "AssistantMessage"}
        result = service._extract_role_from_message(message)
        self.assertEqual(result, "assistant")

    def test_user_message(self) -> None:
        service = CallbackService()
        message = {"_type": "UserMessage"}
        result = service._extract_role_from_message(message)
        self.assertEqual(result, "user")

    def test_system_message(self) -> None:
        service = CallbackService()
        message = {"_type": "SystemMessage"}
        result = service._extract_role_from_message(message)
        self.assertEqual(result, "system")

    def test_unknown_message_type(self) -> None:
        service = CallbackService()
        message = {"_type": "UnknownMessage"}
        result = service._extract_role_from_message(message)
        self.assertEqual(result, "assistant")

    def test_no_type(self) -> None:
        service = CallbackService()
        message = {}
        result = service._extract_role_from_message(message)
        self.assertEqual(result, "assistant")


class TestCallbackServiceShouldSkipActiveRunFallback(unittest.TestCase):
    """Test _should_skip_active_run_fallback method."""

    def test_with_run_id(self) -> None:
        service = CallbackService()
        callback = create_callback_request(run_id="run-1")
        result = service._should_skip_active_run_fallback(callback)
        self.assertFalse(result)

    def test_non_terminal_status(self) -> None:
        service = CallbackService()
        callback = create_callback_request(status=CallbackStatus.RUNNING)
        result = service._should_skip_active_run_fallback(callback)
        self.assertFalse(result)

    def test_with_new_message(self) -> None:
        service = CallbackService()
        callback = create_callback_request(new_message={"_type": "AssistantMessage"})
        result = service._should_skip_active_run_fallback(callback)
        self.assertFalse(result)

    def test_terminal_without_workspace_export(self) -> None:
        service = CallbackService()
        callback = create_callback_request()
        result = service._should_skip_active_run_fallback(callback)
        self.assertFalse(result)

    def test_terminal_with_pending_workspace_export(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="pending")
        result = service._should_skip_active_run_fallback(callback)
        self.assertFalse(result)

    def test_terminal_with_ready_workspace_export(self) -> None:
        service = CallbackService()
        callback = create_callback_request(workspace_export_status="ready")
        result = service._should_skip_active_run_fallback(callback)
        self.assertTrue(result)

    def test_failed_with_ready_workspace_export(self) -> None:
        service = CallbackService()
        callback = create_callback_request(
            status=CallbackStatus.FAILED, workspace_export_status="ready"
        )
        result = service._should_skip_active_run_fallback(callback)
        self.assertTrue(result)


class TestCallbackServiceShouldPreserveExistingReadyWorkspace(unittest.TestCase):
    """Test _should_preserve_existing_ready_workspace method."""

    def test_no_existing_ready_workspace(self) -> None:
        service = CallbackService()
        db_session = MagicMock()
        db_session.workspace_export_status = None
        db_session.workspace_files_prefix = None

        callback = create_callback_request()
        result = service._should_preserve_existing_ready_workspace(db_session, callback)
        self.assertFalse(result)

    def test_existing_ready_workspace_with_incoming_artifacts(self) -> None:
        service = CallbackService()
        db_session = MagicMock()
        db_session.workspace_export_status = "ready"
        db_session.workspace_files_prefix = "files/prefix"
        db_session.workspace_manifest_key = "manifest.json"
        db_session.workspace_archive_key = None

        callback = create_callback_request(
            workspace_export_status="pending",
            workspace_files_prefix="new/prefix",
        )
        result = service._should_preserve_existing_ready_workspace(db_session, callback)
        self.assertFalse(result)

    def test_existing_ready_workspace_incoming_status_ready(self) -> None:
        service = CallbackService()
        db_session = MagicMock()
        db_session.workspace_export_status = "ready"
        db_session.workspace_files_prefix = "files/prefix"

        callback = create_callback_request(workspace_export_status="ready")
        result = service._should_preserve_existing_ready_workspace(db_session, callback)
        self.assertFalse(result)

    def test_existing_ready_workspace_should_preserve(self) -> None:
        service = CallbackService()
        db_session = MagicMock()
        db_session.workspace_export_status = "ready"
        db_session.workspace_files_prefix = "files/prefix"
        db_session.workspace_manifest_key = "manifest.json"
        db_session.workspace_archive_key = None

        callback = create_callback_request(workspace_export_status="pending")
        result = service._should_preserve_existing_ready_workspace(db_session, callback)
        self.assertTrue(result)


class TestCallbackServiceExtractToolExecutions(unittest.TestCase):
    """Test _extract_tool_executions method."""

    def test_non_list_content(self) -> None:
        db = MagicMock()
        service = CallbackService()
        message = {"content": "not a list"}
        service._extract_tool_executions(db, message, uuid.uuid4(), 1)
        # Should not raise

    def test_empty_content(self) -> None:
        db = MagicMock()
        service = CallbackService()
        message = {"content": []}
        service._extract_tool_executions(db, message, uuid.uuid4(), 1)
        # Should not raise

    def test_tool_use_block_missing_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {"_type": "ToolUseBlock", "name": "test_tool"},
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            service._extract_tool_executions(db, message, session_id, 1)
            mock_repo.create.assert_not_called()

    def test_tool_use_block_missing_name(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {"_type": "ToolUseBlock", "id": "tool-1"},
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            service._extract_tool_executions(db, message, session_id, 1)
            mock_repo.create.assert_not_called()

    def test_tool_use_block_creates_new(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {
                    "_type": "ToolUseBlock",
                    "id": "tool-1",
                    "name": "read_file",
                    "input": {"path": "/tmp"},
                },
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            mock_repo.get_by_session_and_tool_use_id.return_value = None
            service._extract_tool_executions(db, message, session_id, 1)
            mock_repo.create.assert_called_once()

    def test_tool_use_block_updates_existing(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {
                    "_type": "ToolUseBlock",
                    "id": "tool-1",
                    "name": "read_file",
                    "input": {"path": "/tmp"},
                },
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            existing = MagicMock()
            mock_repo.get_by_session_and_tool_use_id.return_value = existing
            service._extract_tool_executions(db, message, session_id, 1)
            self.assertEqual(existing.tool_name, "read_file")
            mock_repo.create.assert_not_called()

    def test_tool_result_block_missing_tool_use_id(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {"_type": "ToolResultBlock", "content": "result"},
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            service._extract_tool_executions(db, message, session_id, 1)
            mock_repo.create.assert_not_called()

    def test_tool_result_block_creates_new(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {
                    "_type": "ToolResultBlock",
                    "tool_use_id": "tool-1",
                    "content": "result",
                    "is_error": False,
                },
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            mock_repo.get_by_session_and_tool_use_id.return_value = None
            service._extract_tool_executions(db, message, session_id, 1)
            mock_repo.create.assert_called_once()

    def test_tool_result_block_updates_existing(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": [
                {
                    "_type": "ToolResultBlock",
                    "tool_use_id": "tool-1",
                    "content": "result",
                    "is_error": True,
                },
            ]
        }
        with patch(
            "app.services.callback_service.ToolExecutionRepository"
        ) as mock_repo:
            existing = MagicMock()
            existing.created_at = datetime.now(timezone.utc)
            mock_repo.get_by_session_and_tool_use_id.return_value = existing
            service._extract_tool_executions(db, message, session_id, 1)
            self.assertEqual(existing.is_error, True)

    def test_non_dict_block(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "content": ["not a dict", {"_type": "TextBlock", "text": "hello"}],
        }
        service._extract_tool_executions(db, message, session_id, 1)
        # Should not raise


class TestCallbackServiceExtractAndPersistUsage(unittest.TestCase):
    """Test _extract_and_persist_usage method."""

    def test_non_result_message(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        service = CallbackService()
        message = {"_type": "AssistantMessage"}
        service._extract_and_persist_usage(db, db_session, None, message)
        # Should not persist

    def test_result_message_without_usage(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        service = CallbackService()
        message = {"_type": "ResultMessage"}
        service._extract_and_persist_usage(db, db_session, None, message)
        # Should not persist

    def test_result_message_with_usage(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "total_cost_usd": 0.05,
            "duration_ms": 1000,
        }
        with patch("app.services.callback_service.UsageLogRepository") as mock_repo:
            with patch(
                "app.services.callback_service.normalize_usage_payload"
            ) as mock_normalize:
                mock_normalize.return_value = {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "total_tokens": 150,
                }
                service._extract_and_persist_usage(db, db_session, None, message)
                mock_repo.create.assert_called_once()

    def test_result_message_with_run(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        with patch("app.services.callback_service.UsageLogRepository") as mock_repo:
            with patch(
                "app.services.callback_service.normalize_usage_payload"
            ) as mock_normalize:
                mock_normalize.return_value = {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "total_tokens": 150,
                }
                service._extract_and_persist_usage(db, db_session, db_run, message)
                mock_repo.create.assert_called_once()


class TestCallbackServiceShouldSkipDuplicateResultMessage(unittest.TestCase):
    """Test _should_skip_duplicate_result_message method."""

    def test_non_result_message(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {"_type": "AssistantMessage"}
        result = service._should_skip_duplicate_result_message(db, session_id, message)
        self.assertFalse(result)

    def test_result_message_with_structured_output(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "structured_output": {"key": "value"},
        }
        result = service._should_skip_duplicate_result_message(db, session_id, message)
        self.assertFalse(result)

    def test_result_message_empty_text(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "content": [],
        }
        result = service._should_skip_duplicate_result_message(db, session_id, message)
        self.assertFalse(result)

    def test_no_latest_message(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "content": [{"_type": "TextBlock", "text": "Hello"}],
        }
        with patch("app.services.callback_service.MessageRepository") as mock_repo:
            mock_repo.get_latest_by_session.return_value = None
            result = service._should_skip_duplicate_result_message(
                db, session_id, message
            )
            self.assertFalse(result)

    def test_latest_message_not_assistant(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "ResultMessage",
            "content": [{"_type": "TextBlock", "text": "Hello"}],
        }
        latest = MagicMock()
        latest.role = "user"
        with patch("app.services.callback_service.MessageRepository") as mock_repo:
            mock_repo.get_latest_by_session.return_value = latest
            result = service._should_skip_duplicate_result_message(
                db, session_id, message
            )
            self.assertFalse(result)


class TestCallbackServicePersistMessageAndTools(unittest.TestCase):
    """Test _persist_message_and_tools method."""

    def test_persists_assistant_message(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        message = {
            "_type": "AssistantMessage",
            "content": [{"_type": "TextBlock", "text": "Hello"}],
        }
        with patch("app.services.callback_service.MessageRepository") as mock_repo:
            mock_message = MagicMock()
            mock_message.id = 1
            mock_repo.create.return_value = mock_message
            result = service._persist_message_and_tools(db, session_id, message)
            self.assertIsNotNone(result)

    def test_truncates_text_preview(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        service = CallbackService()
        long_text = "x" * 1000
        message = {
            "_type": "AssistantMessage",
            "content": [{"_type": "TextBlock", "text": long_text}],
        }
        with patch("app.services.callback_service.MessageRepository") as mock_repo:
            mock_message = MagicMock()
            mock_message.id = 1
            mock_repo.create.return_value = mock_message
            service._persist_message_and_tools(db, session_id, message)
            # Check that text_preview was truncated
            call_kwargs = mock_repo.create.call_args.kwargs
            self.assertLessEqual(len(call_kwargs["text_preview"] or ""), 500)


class TestCallbackServiceShouldApplyWorkspaceExport(unittest.TestCase):
    """Test _should_apply_workspace_export method."""

    def test_no_workspace_export_payload(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        service = CallbackService()
        callback = create_callback_request(
            workspace_files_prefix=None,
            workspace_manifest_key=None,
            workspace_archive_key=None,
            workspace_export_status=None,
        )
        result = service._should_apply_workspace_export(db, db_session, None, callback)
        self.assertTrue(result)

    def test_with_workspace_payload_no_run(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        service = CallbackService()
        callback = create_callback_request(workspace_files_prefix="files/")
        result = service._should_apply_workspace_export(db, db_session, None, callback)
        self.assertTrue(result)

    def test_with_run_no_terminal_run(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        service = CallbackService()
        callback = create_callback_request(workspace_files_prefix="files/")
        with patch("app.services.callback_service.RunRepository") as mock_repo:
            mock_repo.get_latest_terminal_by_session.return_value = None
            result = service._should_apply_workspace_export(
                db, db_session, db_run, callback
            )
            self.assertTrue(result)

    def test_with_run_same_as_terminal(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        service = CallbackService()
        callback = create_callback_request(workspace_files_prefix="files/")
        with patch("app.services.callback_service.RunRepository") as mock_repo:
            mock_repo.get_latest_terminal_by_session.return_value = db_run
            result = service._should_apply_workspace_export(
                db, db_session, db_run, callback
            )
            self.assertTrue(result)

    def test_ready_status_with_stale_run_is_rejected(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_session.workspace_export_status = "pending"  # Not "ready"
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        terminal_run = MagicMock()
        terminal_run.id = uuid.uuid4()  # Different from db_run
        service = CallbackService()
        callback = create_callback_request(
            workspace_files_prefix="files/",
            workspace_export_status="ready",
        )
        with patch("app.services.callback_service.RunRepository") as mock_repo:
            mock_repo.get_latest_terminal_by_session.return_value = terminal_run
            result = service._should_apply_workspace_export(
                db, db_session, db_run, callback
            )
            self.assertFalse(result)

    def test_stale_run_non_ready_status(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_session.workspace_export_status = "ready"  # Already has ready
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        terminal_run = MagicMock()
        terminal_run.id = uuid.uuid4()  # Different from db_run
        service = CallbackService()
        callback = create_callback_request(
            workspace_files_prefix="files/",
            workspace_export_status="pending",
        )
        with patch("app.services.callback_service.RunRepository") as mock_repo:
            mock_repo.get_latest_terminal_by_session.return_value = terminal_run
            result = service._should_apply_workspace_export(
                db, db_session, db_run, callback
            )
            # Should return False - stale run and not a "ready" status upgrade
            self.assertFalse(result)


class TestCallbackServiceResolveSessionAndRun(unittest.TestCase):
    """Test _resolve_session_and_run method."""

    def test_with_run_id_found(self) -> None:
        db = MagicMock()
        service = CallbackService()
        run_id = uuid.uuid4()
        session_id = uuid.uuid4()
        db_run = MagicMock()
        db_run.session_id = session_id
        db_session = MagicMock()

        with patch("app.services.callback_service.RunRepository") as run_repo:
            with patch(
                "app.services.callback_service.SessionRepository"
            ) as session_repo:
                run_repo.get_by_id.return_value = db_run
                session_repo.get_by_id_for_update.return_value = db_session

                callback = create_callback_request(run_id=str(run_id))
                result = service._resolve_session_and_run(db, callback, run_id)

                self.assertEqual(result, (db_session, db_run))

    def test_with_run_id_not_found(self) -> None:
        db = MagicMock()
        service = CallbackService()
        run_id = uuid.uuid4()

        with patch("app.services.callback_service.RunRepository") as run_repo:
            run_repo.get_by_id.return_value = None

            callback = create_callback_request(run_id=str(run_id), session_id="sdk-123")
            with patch(
                "app.services.callback_service.session_service"
            ) as mock_session_svc:
                mock_session_svc.find_session_by_sdk_id_or_uuid.return_value = None
                result = service._resolve_session_and_run(db, callback, run_id)

                self.assertEqual(result, (None, None))

    def test_without_run_id_session_found(self) -> None:
        db = MagicMock()
        service = CallbackService()
        session_id = uuid.uuid4()
        db_session = create_mock_db_session(session_id=session_id)
        db_run = MagicMock()

        with patch("app.services.callback_service.SessionRepository") as session_repo:
            with patch("app.services.callback_service.RunRepository") as run_repo:
                session_repo.get_by_id_for_update.return_value = db_session
                run_repo.get_latest_active_by_session.return_value = db_run

                with patch(
                    "app.services.callback_service.session_service"
                ) as mock_session_svc:
                    mock_session_ref = MagicMock()
                    mock_session_ref.id = session_id
                    mock_session_svc.find_session_by_sdk_id_or_uuid.return_value = (
                        mock_session_ref
                    )

                    callback = create_callback_request(session_id="sdk-123")
                    result = service._resolve_session_and_run(db, callback, None)

                    self.assertEqual(result, (db_session, db_run))

    def test_without_run_id_session_not_found(self) -> None:
        db = MagicMock()
        service = CallbackService()

        with patch("app.services.callback_service.session_service") as mock_session_svc:
            mock_session_svc.find_session_by_sdk_id_or_uuid.return_value = None

            callback = create_callback_request(session_id="sdk-123")
            result = service._resolve_session_and_run(db, callback, None)

            self.assertEqual(result, (None, None))

    def test_skip_active_run_fallback(self) -> None:
        db = MagicMock()
        service = CallbackService()
        session_id = uuid.uuid4()
        db_session = create_mock_db_session(session_id=session_id)

        with patch("app.services.callback_service.SessionRepository") as session_repo:
            session_repo.get_by_id_for_update.return_value = db_session

            with patch(
                "app.services.callback_service.session_service"
            ) as mock_session_svc:
                mock_session_ref = MagicMock()
                mock_session_ref.id = session_id
                mock_session_svc.find_session_by_sdk_id_or_uuid.return_value = (
                    mock_session_ref
                )

                # Terminal status with ready workspace export and no new_message
                callback = create_callback_request(
                    workspace_export_status="ready",
                    new_message=None,
                )
                result = service._resolve_session_and_run(db, callback, None)

                # Should return (db_session, None) because skip is True
                self.assertEqual(result, (db_session, None))


class TestCallbackServiceDetectDeliverablesIfReady(unittest.TestCase):
    """Test _detect_deliverables_if_ready method."""

    def test_not_ready_status(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        service = CallbackService()

        callback = create_callback_request(workspace_export_status="pending")
        service._detect_deliverables_if_ready(
            db=db, db_session=db_session, db_run=None, callback=callback
        )
        # Should not call detect

    def test_no_manifest_key(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.workspace_manifest_key = ""
        service = CallbackService()

        callback = create_callback_request(workspace_export_status="ready")
        service._detect_deliverables_if_ready(
            db=db, db_session=db_session, db_run=None, callback=callback
        )
        # Should not call detect

    def test_with_run(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.workspace_manifest_key = "manifest.json"
        db_run = MagicMock()

        service = CallbackService()

        callback = create_callback_request(workspace_export_status="ready")
        with patch.object(
            service._deliverable_detection, "detect_for_completed_run"
        ) as mock_detect:
            service._detect_deliverables_if_ready(
                db=db, db_session=db_session, db_run=db_run, callback=callback
            )
            mock_detect.assert_called_once_with(db, session=db_session, run=db_run)

    def test_without_run_finds_terminal(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_session.workspace_manifest_key = "manifest.json"
        terminal_run = MagicMock()

        service = CallbackService()

        callback = create_callback_request(workspace_export_status="ready")
        with patch("app.services.callback_service.RunRepository") as run_repo:
            with patch.object(
                service._deliverable_detection, "detect_for_completed_run"
            ) as mock_detect:
                run_repo.get_latest_terminal_by_session.return_value = terminal_run
                service._detect_deliverables_if_ready(
                    db=db, db_session=db_session, db_run=None, callback=callback
                )
                mock_detect.assert_called_once()

    def test_without_run_no_terminal(self) -> None:
        db = MagicMock()
        db_session = MagicMock()
        db_session.id = uuid.uuid4()
        db_session.workspace_manifest_key = "manifest.json"

        service = CallbackService()

        callback = create_callback_request(workspace_export_status="ready")
        with patch("app.services.callback_service.RunRepository") as run_repo:
            with patch.object(
                service._deliverable_detection, "detect_for_completed_run"
            ) as mock_detect:
                run_repo.get_latest_terminal_by_session.return_value = None
                service._detect_deliverables_if_ready(
                    db=db, db_session=db_session, db_run=None, callback=callback
                )
                mock_detect.assert_not_called()


class TestCallbackServiceProcessAgentCallback(unittest.TestCase):
    """Test process_agent_callback method."""

    def test_session_not_found(self) -> None:
        db = MagicMock()
        service = CallbackService()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (None, None)

            callback = create_callback_request(session_id="unknown-session")
            result = service.process_agent_callback(db, callback)

            self.assertEqual(result.status, "callback_received")
            assert result.message is not None
            self.assertIn("not found", result.message)

    def test_canceled_session(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session(status="canceled")

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, None)

            callback = create_callback_request()
            result = service.process_agent_callback(db, callback)

            self.assertEqual(result.status, "canceled")

    def test_stale_ready_export_callback_does_not_trigger_detection(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session(
            status="running",
            workspace_export_status="pending",
            workspace_manifest_key="manifest.json",
        )
        db_session.id = uuid.uuid4()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()
        newer_terminal_run = MagicMock()
        newer_terminal_run.id = uuid.uuid4()

        with (
            patch.object(service, "_resolve_session_and_run") as mock_resolve,
            patch.object(
                service,
                "_detect_deliverables_if_ready",
            ) as mock_detect_deliverables,
            patch("app.services.callback_service.RunRepository") as mock_run_repo,
            patch("app.services.callback_service.run_lifecycle_service"),
            patch("app.services.callback_service.session_queue_service") as mock_queue,
            patch(
                "app.services.callback_service.pending_skill_creation_service"
            ) as mock_pending_skill_creation,
        ):
            mock_resolve.return_value = (db_session, db_run)
            mock_run_repo.get_latest_terminal_by_session.return_value = (
                newer_terminal_run
            )
            mock_queue.has_active_items.return_value = False
            service._im_events = MagicMock()

            callback = create_callback_request(
                run_id=str(db_run.id),
                workspace_manifest_key="manifest.json",
                workspace_export_status="ready",
            )
            callback.progress = 100

            service.process_agent_callback(db, callback)

            mock_detect_deliverables.assert_not_called()
            mock_pending_skill_creation.detect_and_create_pending.assert_called_once()

    def test_updates_sdk_session_id_from_message(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session(sdk_session_id="old-sdk-id")

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, None)

            callback = create_callback_request(
                new_message={
                    "_type": "ResultMessage",
                    "session_id": "new-sdk-id",
                }
            )
            with patch("app.services.deliverable_detection_service.S3StorageService"):
                service.process_agent_callback(db, callback)

                self.assertEqual(db_session.sdk_session_id, "new-sdk-id")
                db.commit.assert_called_once()

    def test_persists_new_message(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, None)

            with patch.object(
                service, "_should_skip_duplicate_result_message"
            ) as mock_skip:
                mock_skip.return_value = False

                with patch.object(
                    service, "_persist_message_and_tools"
                ) as mock_persist:
                    mock_message = MagicMock()
                    mock_persist.return_value = mock_message

                    callback = create_callback_request(
                        status=CallbackStatus.RUNNING,
                        new_message={
                            "_type": "AssistantMessage",
                            "content": [{"_type": "TextBlock", "text": "Hello"}],
                        },
                    )
                    with patch(
                        "app.services.deliverable_detection_service.S3StorageService"
                    ):
                        service.process_agent_callback(db, callback)

                        mock_persist.assert_called_once()

    def test_skips_duplicate_message(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, None)

            with patch.object(
                service, "_should_skip_duplicate_result_message"
            ) as mock_skip:
                mock_skip.return_value = True

                with patch.object(
                    service, "_persist_message_and_tools"
                ) as mock_persist:
                    with patch(
                        "app.services.deliverable_detection_service.S3StorageService"
                    ):
                        callback = create_callback_request(
                            new_message={"_type": "ResultMessage"}
                        )
                        service.process_agent_callback(db, callback)

                        mock_persist.assert_not_called()

    def test_applies_workspace_export(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, None)

            with patch.object(service, "_should_apply_workspace_export") as mock_apply:
                mock_apply.return_value = True

                with patch.object(
                    service, "_should_preserve_existing_ready_workspace"
                ) as mock_preserve:
                    mock_preserve.return_value = False

                    with patch(
                        "app.services.deliverable_detection_service.S3StorageService"
                    ):
                        callback = create_callback_request(
                            workspace_files_prefix="files/",
                            workspace_manifest_key="manifest.json",
                            workspace_archive_key="archive.zip",
                            workspace_export_status="ready",
                        )
                        service.process_agent_callback(db, callback)

                        self.assertEqual(db_session.workspace_files_prefix, "files/")
                        self.assertEqual(
                            db_session.workspace_manifest_key, "manifest.json"
                        )
                        self.assertEqual(
                            db_session.workspace_archive_key, "archive.zip"
                        )
                        self.assertEqual(db_session.workspace_export_status, "ready")

    def test_run_completed(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, db_run)

            with patch(
                "app.services.callback_service.run_lifecycle_service"
            ) as mock_lifecycle:
                with patch(
                    "app.services.deliverable_detection_service.S3StorageService"
                ):
                    callback = create_callback_request(status=CallbackStatus.COMPLETED)
                    service.process_agent_callback(db, callback)

                    self.assertEqual(db_run.progress, 100)
                    mock_lifecycle.finalize_terminal.assert_called_once()

    def test_run_failed(self) -> None:
        db = MagicMock()
        service = CallbackService()
        db_session = create_mock_db_session()
        db_run = MagicMock()
        db_run.id = uuid.uuid4()

        with patch.object(service, "_resolve_session_and_run") as mock_resolve:
            mock_resolve.return_value = (db_session, db_run)

            with patch(
                "app.services.callback_service.run_lifecycle_service"
            ) as mock_lifecycle:
                with patch(
                    "app.services.deliverable_detection_service.S3StorageService"
                ):
                    callback = create_callback_request(
                        status=CallbackStatus.FAILED,
                        error_message="Something went wrong",
                    )
                    service.process_agent_callback(db, callback)

                    mock_lifecycle.finalize_terminal.assert_called_once_with(
                        db,
                        db_run,
                        status="failed",
                        error_message="Something went wrong",
                    )


class TestExtractVisibleMessageText(unittest.TestCase):
    """Test _extract_visible_message_text helper function."""

    def test_text_block_content(self) -> None:
        from app.services.callback_service import _extract_visible_message_text

        message = {
            "content": [
                {"_type": "TextBlock", "text": "Hello"},
                {"_type": "TextBlock", "text": "World"},
            ]
        }
        result = _extract_visible_message_text(message)
        self.assertEqual(result, "Hello\n\nWorld")

    def test_result_field(self) -> None:
        from app.services.callback_service import _extract_visible_message_text

        message = {"result": "Task completed"}
        result = _extract_visible_message_text(message)
        self.assertEqual(result, "Task completed")

    def test_text_field(self) -> None:
        from app.services.callback_service import _extract_visible_message_text

        message = {"text": "Plain text"}
        result = _extract_visible_message_text(message)
        self.assertEqual(result, "Plain text")

    def test_no_text(self) -> None:
        from app.services.callback_service import _extract_visible_message_text

        message = {"content": []}
        result = _extract_visible_message_text(message)
        self.assertIsNone(result)

    def test_empty_text_blocks(self) -> None:
        from app.services.callback_service import _extract_visible_message_text

        message = {
            "content": [
                {"_type": "TextBlock", "text": ""},
                {"_type": "TextBlock", "text": "   "},
            ]
        }
        result = _extract_visible_message_text(message)
        self.assertIsNone(result)


class TestNormalizeVisibleMessageText(unittest.TestCase):
    """Test _normalize_visible_message_text helper function."""

    def test_none_input(self) -> None:
        from app.services.callback_service import _normalize_visible_message_text

        result = _normalize_visible_message_text(None)
        self.assertEqual(result, "")

    def test_empty_string(self) -> None:
        from app.services.callback_service import _normalize_visible_message_text

        result = _normalize_visible_message_text("")
        self.assertEqual(result, "")

    def test_removes_replacement_char(self) -> None:
        from app.services.callback_service import _normalize_visible_message_text

        result = _normalize_visible_message_text("Hello\ufffdWorld")
        self.assertEqual(result, "HelloWorld")

    def test_strips_whitespace(self) -> None:
        from app.services.callback_service import _normalize_visible_message_text

        result = _normalize_visible_message_text("  Hello World  ")
        self.assertEqual(result, "Hello World")


if __name__ == "__main__":
    unittest.main()
