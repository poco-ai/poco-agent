import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.server_channel_message import ServerChannelMessage
from app.services.session_service import SessionService


class SessionServiceCancellationProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionService()
        self.db = MagicMock()
        self.session_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()

    def test_sync_channel_execution_cancellation_marks_placeholder_canceled(
        self,
    ) -> None:
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "running",
                "summary": "Still working",
            },
            text_preview="Still working",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={"channel_id": str(self.channel_id)},
        )

        with patch(
            "app.services.session_service.ServerChannelMessageRepository.list_session_projections",
            return_value=[placeholder],
        ):
            self.service._sync_channel_execution_cancellation(
                self.db,
                db_session=db_session,
                execution_status="canceled",
            )

        self.assertEqual(placeholder.content["execution_status"], "canceled")
        self.assertEqual(placeholder.content["summary"], "Execution canceled.")
        self.assertEqual(placeholder.text_preview, "Execution canceled.")

    def test_sync_channel_execution_cancellation_rewrites_agent_session_projection(
        self,
    ) -> None:
        projection = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_session",
                "session_id": str(self.session_id),
                "text": "@coworker is preparing a response.",
                "actor_label": "coworker",
                "agent_handle": "coworker",
            },
            text_preview="@coworker is preparing a response.",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={"channel_id": str(self.channel_id)},
        )

        with patch(
            "app.services.session_service.ServerChannelMessageRepository.list_session_projections",
            return_value=[projection],
        ):
            self.service._sync_channel_execution_cancellation(
                self.db,
                db_session=db_session,
                execution_status="canceled",
            )

        self.assertEqual(projection.content["source"], "agent_execution")
        self.assertEqual(projection.content["execution_status"], "canceled")
        self.assertEqual(projection.content["agent_handle"], "coworker")
        self.assertEqual(projection.content["summary"], "Execution canceled.")

    def test_sync_channel_execution_cancellation_updates_all_open_projections_for_session(
        self,
    ) -> None:
        first_projection = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "running",
                "summary": "Running",
            },
            text_preview="Running",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        second_projection = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_session",
                "session_id": str(self.session_id),
                "text": "Preparing",
            },
            text_preview="Preparing",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={"channel_id": str(self.channel_id)},
        )

        with patch(
            "app.services.session_service.ServerChannelMessageRepository.list_session_projections",
            return_value=[first_projection, second_projection],
        ):
            self.service._sync_channel_execution_cancellation(
                self.db,
                db_session=db_session,
                execution_status="canceled",
            )

        for projection in [first_projection, second_projection]:
            self.assertEqual(projection.content["source"], "agent_execution")
            self.assertEqual(projection.content["execution_status"], "canceled")
            self.assertEqual(projection.content["summary"], "Execution canceled.")
            self.assertEqual(projection.text_preview, "Execution canceled.")

    def test_release_agent_runtime_on_cancellation_releases_persistent_session(
        self,
    ) -> None:
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "agent_identity_id": str(uuid.uuid4()),
                "agent_runtime_mode": "persistent",
            },
        )

        with patch(
            "app.services.session_service.PersistentRuntimeService.release_runtime_for_session"
        ) as release_runtime:
            self.service._release_agent_runtime_on_cancellation(
                self.db,
                db_session=db_session,
                callback_status="canceled",
            )

        release_runtime.assert_called_once_with(
            self.db,
            session_id=self.session_id,
            callback_status="canceled",
        )


if __name__ == "__main__":
    unittest.main()
