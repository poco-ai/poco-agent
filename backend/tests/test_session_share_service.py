import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.session_share import SessionShare
from app.schemas.session_share import (
    SessionShareCreateRequest,
    SessionShareToChannelRequest,
)
from app.services.session_share_service import SessionShareService


class SessionShareServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SessionShareService()
        self.db = MagicMock()
        self.session_id = uuid.uuid4()
        self.share_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.now = datetime.now(UTC)

    def test_sanitize_config_for_fork_removes_channel_runtime(self) -> None:
        share = SessionShare(
            id=self.share_id,
            source_session_id=self.session_id,
            owner_user_id="owner",
            token="token",
            is_revoked=False,
            created_at=self.now,
            updated_at=self.now,
        )

        result = self.service._sanitize_config_for_fork(
            {
                "model": "claude-sonnet",
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(uuid.uuid4()),
                "thread_root_message_id": str(uuid.uuid4()),
                "trigger_context": {"version": 1},
                "persistent_runtime_key": "channel:agent",
                "filesystem_mode": "local_mount",
                "local_mounts": [{"id": "local", "host_path": "/tmp"}],
            },
            share=share,
        )

        assert result is not None
        self.assertEqual(result["model"], "claude-sonnet")
        self.assertEqual(result["filesystem_mode"], "sandbox")
        self.assertEqual(result["local_mounts"], [])
        self.assertEqual(result["source_share_id"], str(self.share_id))
        self.assertEqual(result["source_session_id"], str(self.session_id))
        self.assertNotIn("server_id", result)
        self.assertNotIn("channel_id", result)
        self.assertNotIn("agent_identity_id", result)
        self.assertNotIn("thread_root_message_id", result)
        self.assertNotIn("trigger_context", result)
        self.assertNotIn("persistent_runtime_key", result)

    def test_create_share_persists_owner_token_and_source(self) -> None:
        source_session = AgentSession(
            id=self.session_id,
            user_id="owner",
            title="Demo",
            kind="chat",
            status="completed",
            created_at=self.now,
            updated_at=self.now,
        )

        def create_share(_db, share: SessionShare):
            share.id = self.share_id
            share.created_at = self.now
            share.updated_at = self.now
            return share

        with (
            patch(
                "app.services.session_share_service.SessionRepository.get_by_id",
                return_value=source_session,
            ),
            patch(
                "app.services.session_share_service.SessionShareRepository.get_by_token",
                return_value=None,
            ),
            patch(
                "app.services.session_share_service.SessionShareRepository.create",
                side_effect=create_share,
            ) as create_repository_share,
        ):
            result = self.service.create_share(
                self.db,
                session_id=self.session_id,
                owner_user_id="owner",
                request=SessionShareCreateRequest(title="Shared demo"),
            )

        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(result)
        created = create_repository_share.call_args.args[1]
        self.assertEqual(created.source_session_id, self.session_id)
        self.assertEqual(created.owner_user_id, "owner")
        self.assertEqual(created.title, "Shared demo")
        self.assertTrue(created.token)

    def test_get_snapshot_returns_messages_runs_and_timeline(self) -> None:
        share = SessionShare(
            id=self.share_id,
            source_session_id=self.session_id,
            owner_user_id="owner",
            token="token",
            title="Demo",
            is_revoked=False,
            created_at=self.now,
            updated_at=self.now,
        )
        source_session = AgentSession(
            id=self.session_id,
            user_id="owner",
            title="Demo",
            kind="chat",
            status="completed",
            created_at=self.now,
            updated_at=self.now,
        )
        message = AgentMessage(
            id=1,
            session_id=self.session_id,
            role="user",
            content={"text": "hello"},
            text_preview="hello",
            created_at=self.now,
            updated_at=self.now,
        )
        run = AgentRun(
            id=uuid.uuid4(),
            session_id=self.session_id,
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            attempts=1,
            created_at=self.now,
            updated_at=self.now,
            scheduled_at=self.now,
        )

        with (
            patch(
                "app.services.session_share_service.SessionShareRepository.get_active_by_token",
                return_value=share,
            ),
            patch(
                "app.services.session_share_service.SessionRepository.get_by_id",
                return_value=source_session,
            ),
            patch(
                "app.services.session_share_service.MessageRepository.list_by_session",
                return_value=[message],
            ),
            patch(
                "app.services.session_share_service.RunRepository.list_by_session",
                return_value=[run],
            ),
            patch(
                "app.services.session_share_service.ToolExecutionRepository.count_by_run_ids",
                return_value={run.id: 2},
            ),
        ):
            snapshot = self.service.get_snapshot(self.db, token="token")

        self.assertEqual(snapshot.share.share_id, self.share_id)
        self.assertEqual(snapshot.session.session_id, self.session_id)
        self.assertEqual(snapshot.messages[0].id, 1)
        self.assertEqual(snapshot.runs[0].run_id, run.id)
        self.assertEqual(snapshot.runs[0].replay_step_count, 2)
        self.assertEqual(len(snapshot.timeline), 2)

    def test_fork_share_clones_to_target_user(self) -> None:
        share = SessionShare(
            id=self.share_id,
            source_session_id=self.session_id,
            owner_user_id="owner",
            token="token",
            title="Demo",
            is_revoked=False,
            created_at=self.now,
            updated_at=self.now,
        )
        source_session = AgentSession(
            id=self.session_id,
            user_id="owner",
            title="Demo",
            kind="chat",
            status="completed",
            created_at=self.now,
            updated_at=self.now,
        )
        forked_session = AgentSession(
            id=uuid.uuid4(),
            user_id="user-2",
            title="Demo",
            kind="chat",
            status="completed",
            created_at=self.now,
            updated_at=self.now,
        )

        with (
            patch(
                "app.services.session_share_service.SessionShareRepository.get_active_by_token",
                return_value=share,
            ),
            patch(
                "app.services.session_share_service.SessionRepository.get_by_id",
                return_value=source_session,
            ),
            patch.object(
                self.service,
                "_clone_session_for_share_fork",
                return_value=forked_session,
            ) as clone_session,
        ):
            result = self.service.fork_share(
                self.db,
                token="token",
                target_user_id="user-2",
            )

        clone_session.assert_called_once_with(
            self.db,
            share=share,
            source_session=source_session,
            target_user_id="user-2",
        )
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(forked_session)
        self.assertEqual(result.session_id, forked_session.id)
        self.assertEqual(result.source_session_id, self.session_id)
        self.assertEqual(result.share_id, self.share_id)

    def test_share_to_channel_creates_event_and_thread_without_send_message(
        self,
    ) -> None:
        share = SessionShare(
            id=self.share_id,
            source_session_id=self.session_id,
            owner_user_id="owner",
            token="token",
            title="Demo",
            is_revoked=False,
            created_at=self.now,
            updated_at=self.now,
        )
        source_session = AgentSession(
            id=self.session_id,
            user_id="owner",
            title="Demo",
            kind="chat",
            status="completed",
            created_at=self.now,
            updated_at=self.now,
        )
        user_message = AgentMessage(
            id=1,
            session_id=self.session_id,
            role="user",
            content={"text": "@agent summarize this"},
            text_preview="@agent summarize this",
            created_at=self.now,
            updated_at=self.now,
        )
        assistant_message = AgentMessage(
            id=2,
            session_id=self.session_id,
            role="assistant",
            content={"text": "Summary"},
            text_preview="Summary",
            created_at=self.now,
            updated_at=self.now,
        )
        run = AgentRun(
            id=uuid.uuid4(),
            session_id=self.session_id,
            user_message_id=1,
            status="completed",
            permission_mode="default",
            progress=100,
            schedule_mode="immediate",
            attempts=1,
            created_at=self.now,
            updated_at=self.now,
            scheduled_at=self.now,
            started_at=self.now,
            finished_at=self.now,
        )
        channel = ServerChannel(
            id=self.channel_id,
            server_id=self.server_id,
            name="general",
            slug="general",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=self.now,
            updated_at=self.now,
        )
        created_messages: list[ServerChannelMessage] = []

        def create_message(_db, message: ServerChannelMessage):
            message.id = uuid.uuid4()
            message.created_at = self.now
            message.updated_at = self.now
            created_messages.append(message)
            return message

        def create_event(_db, **kwargs):
            message = ServerChannelMessage(
                id=uuid.uuid4(),
                channel_id=kwargs["channel_id"],
                author_user_id=None,
                message_type="event",
                content={"event_type": kwargs["event_type"], **kwargs["content"]},
                text_preview=kwargs["text_preview"],
                thread_root_message_id=kwargs.get("thread_root_message_id"),
                created_at=self.now,
                updated_at=self.now,
            )
            return message

        with (
            patch(
                "app.services.session_share_service.SessionShareRepository.get_active_by_token",
                return_value=share,
            ),
            patch(
                "app.services.session_share_service.SessionRepository.get_by_id",
                return_value=source_session,
            ),
            patch(
                "app.services.session_share_service.require_channel_member_access",
                return_value=channel,
            ),
            patch(
                "app.services.session_share_service.MessageRepository.list_by_session",
                return_value=[user_message, assistant_message],
            ),
            patch(
                "app.services.session_share_service.RunRepository.list_by_session",
                return_value=[run],
            ),
            patch(
                "app.services.session_share_service.ServerChannelMessageRepository.create",
                side_effect=create_message,
            ),
            patch(
                "app.services.session_share_service.create_channel_event_message",
                side_effect=create_event,
            ) as create_event_message,
            patch(
                "app.services.server_channel_message_service.ServerAgentTriggerService.trigger_for_channel_message"
            ) as trigger_for_channel_message,
        ):
            result = self.service.share_to_channel(
                self.db,
                token="token",
                current_user_id="user-1",
                request=SessionShareToChannelRequest(
                    server_id=self.server_id,
                    channel_id=self.channel_id,
                ),
            )

        self.db.commit.assert_called_once()
        create_event_message.assert_called_once()
        trigger_for_channel_message.assert_not_called()
        self.assertEqual(len(created_messages), 2)
        root, reply = created_messages
        self.assertEqual(root.message_type, "user")
        self.assertIsNone(root.thread_root_message_id)
        self.assertEqual(root.content["source"], "imported_chat_session")
        self.assertEqual(reply.message_type, "system")
        self.assertEqual(reply.thread_root_message_id, root.id)
        self.assertEqual(reply.content["source"], "imported_agent_session")
        self.assertEqual(reply.content["source_run_id"], str(run.id))
        self.assertEqual(result.thread.root.message_id, root.id)


if __name__ == "__main__":
    unittest.main()
