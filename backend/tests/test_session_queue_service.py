import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.session_queue_service import SessionQueueService


class SessionQueueServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionQueueService()
        self.db = MagicMock()
        self.db_session = SimpleNamespace(
            id=uuid.uuid4(),
            status="idle",
            state_patch={},
            workspace_archive_url=None,
            workspace_files_prefix=None,
            workspace_manifest_key=None,
            workspace_archive_key=None,
            workspace_export_status=None,
            cancellation_requested_at=None,
            cancellation_completed_at=None,
            cancellation_target_run_id=None,
            cancellation_target_worker_id=None,
            cancellation_reason=None,
            cancellation_claimed_by=None,
            cancellation_lease_expires_at=None,
            cancellation_error=None,
            config_snapshot=None,
        )

    def test_materialize_run_persists_trigger_context_in_message_metadata(self) -> None:
        trigger_context = {
            "version": 1,
            "trigger_type": "channel_mention",
            "server_id": str(uuid.uuid4()),
            "channel_id": str(uuid.uuid4()),
            "trigger_message_id": str(uuid.uuid4()),
            "target_agent_identity_id": str(uuid.uuid4()),
            "target_agent_handle": "reviewer",
            "source_actor": {"actor_type": "user", "user_id": "user-1"},
        }
        db_message = SimpleNamespace(id=123)
        db_run = SimpleNamespace(id=uuid.uuid4())

        with (
            patch(
                "app.services.session_queue_service.MessageRepository.create",
                return_value=db_message,
            ) as create_message,
            patch(
                "app.services.session_queue_service.RunRepository.create",
                return_value=db_run,
            ),
        ):
            self.service.materialize_run(
                self.db,
                db_session=self.db_session,
                prompt="Please review this change",
                permission_mode="acceptEdits",
                schedule_mode="immediate",
                run_config_snapshot={"trigger_context": trigger_context},
            )

        content = create_message.call_args.kwargs["content"]
        self.assertEqual(content["metadata"]["trigger_context"], trigger_context)
        self.assertEqual(
            create_message.call_args.kwargs["text_preview"],
            "Please review this change",
        )

    def test_materialize_run_persists_file_references_in_message_metadata(self) -> None:
        file_references = [
            {
                "id": "ref-1",
                "kind": "workspace_file",
                "sessionId": str(self.db_session.id),
                "path": "/reports/summary.md",
                "insertedText": "#summary.md",
                "displayName": "summary.md",
            }
        ]
        db_message = SimpleNamespace(id=123)
        db_run = SimpleNamespace(id=uuid.uuid4())

        with (
            patch(
                "app.services.session_queue_service.MessageRepository.create",
                return_value=db_message,
            ) as create_message,
            patch(
                "app.services.session_queue_service.RunRepository.create",
                return_value=db_run,
            ),
        ):
            self.service.materialize_run(
                self.db,
                db_session=self.db_session,
                prompt="Please read #summary.md",
                permission_mode="default",
                schedule_mode="immediate",
                run_config_snapshot={"file_references": file_references},
            )

        content = create_message.call_args.kwargs["content"]
        self.assertEqual(content["metadata"]["file_references"], file_references)

    def test_materialize_run_keeps_plain_user_messages_without_metadata(self) -> None:
        db_message = SimpleNamespace(id=123)
        db_run = SimpleNamespace(id=uuid.uuid4())

        with (
            patch(
                "app.services.session_queue_service.MessageRepository.create",
                return_value=db_message,
            ) as create_message,
            patch(
                "app.services.session_queue_service.RunRepository.create",
                return_value=db_run,
            ),
        ):
            self.service.materialize_run(
                self.db,
                db_session=self.db_session,
                prompt="Regular chat prompt",
                permission_mode="default",
                schedule_mode="immediate",
                run_config_snapshot=None,
            )

        content = create_message.call_args.kwargs["content"]
        self.assertNotIn("metadata", content)


if __name__ == "__main__":
    unittest.main()
