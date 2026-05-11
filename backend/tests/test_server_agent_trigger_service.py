import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.user import User
from app.schemas.agent_trigger import AgentTriggerEnvelope
from app.schemas.task import TaskEnqueueResponse
from app.services.server_agent_trigger_service import ServerAgentTriggerService


class ServerAgentTriggerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.task_service = MagicMock()
        self.context_service = MagicMock()
        self.service = ServerAgentTriggerService(
            task_service=self.task_service,
            shared_context_service=self.context_service,
        )
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_id = uuid.uuid4()
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def test_channel_mention_enqueues_run_for_matching_agent(self) -> None:
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist",
            content={"text": "Please review @api-specialist"},
            thread_root_message_id=None,
        )
        channel = SimpleNamespace(
            id=self.channel_id,
            server_id=self.server_id,
            conversation_type="channel",
            direct_agent_identity_id=None,
            name="backend",
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            server_id=self.server_id,
            preset_id=8,
            handle="api-specialist",
            display_name="API Specialist",
            lifecycle_state="active",
            removed_at=None,
            created_by="owner-user",
            persistent_state=SimpleNamespace(active_session_id=None),
        )
        membership = SimpleNamespace(agent_identity_id=self.agent_id, status="active")
        self.context_service.extract_trigger_body.return_value = (
            "Please review @api-specialist"
        )
        self.context_service.build_trigger_envelope.return_value = AgentTriggerEnvelope(
            trigger_type="channel_mention",
            server_id=self.server_id,
            channel_id=self.channel_id,
            trigger_message_id=message.id,
            thread_root_message_id=message.id,
            target_agent_identity_id=self.agent_id,
            target_agent_handle="api-specialist",
            source_actor={"actor_type": "user", "user_id": "user-1"},
            handoff={
                "dedupe_key": f"channel-trigger:{message.id}:{self.agent_id}",
            },
        )
        self.task_service.enqueue_task.return_value = TaskEnqueueResponse(
            session_id=uuid.uuid4(),
            accepted_type="run",
            run_id=uuid.uuid4(),
            status="queued",
            queued_query_count=0,
        )

        with (
            patch(
                "app.services.server_agent_trigger_service.ServerChannelAgentMemberRepository.list_by_channel",
                return_value=[membership],
            ),
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
        ):
            results = self.service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        self.assertEqual(len(results), 1)
        self.context_service.extract_trigger_body.assert_called_once_with(message)
        self.context_service.build_trigger_envelope.assert_called_once()
        self.task_service.enqueue_task.assert_called_once()
        _, owner_user_id, request = self.task_service.enqueue_task.call_args.args
        self.assertEqual(owner_user_id, "owner-user")
        self.assertEqual(request.prompt, "Please review @api-specialist")
        self.assertEqual(request.config.agent_identity_id, self.agent_id)
        self.assertEqual(request.config.channel_id, self.channel_id)
        self.assertEqual(request.config.server_id, self.server_id)
        self.assertEqual(request.config.trigger_type, "channel_mention")
        self.assertEqual(
            request.config.trigger_context.handoff.dedupe_key,
            f"channel-trigger:{message.id}:{self.agent_id}",
        )

    def test_channel_mention_ignores_display_name_match(self) -> None:
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @Reviewer",
            content={"text": "Please review @Reviewer"},
            thread_root_message_id=None,
        )
        channel = SimpleNamespace(
            id=self.channel_id,
            server_id=self.server_id,
            conversation_type="channel",
            direct_agent_identity_id=None,
            name="backend",
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            server_id=self.server_id,
            preset_id=8,
            handle="api-specialist",
            display_name="Reviewer",
            lifecycle_state="active",
            removed_at=None,
            created_by="owner-user",
            persistent_state=SimpleNamespace(active_session_id=None),
        )
        membership = SimpleNamespace(agent_identity_id=self.agent_id, status="active")

        with (
            patch(
                "app.services.server_agent_trigger_service.ServerChannelAgentMemberRepository.list_by_channel",
                return_value=[membership],
            ),
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
        ):
            results = self.service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        self.assertEqual(results, [])
        self.task_service.enqueue_task.assert_not_called()

    def test_agent_dm_message_triggers_direct_agent_without_mention(self) -> None:
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Can you continue this work?",
            content={"text": "Can you continue this work?"},
            thread_root_message_id=None,
        )
        channel = SimpleNamespace(
            id=self.channel_id,
            server_id=self.server_id,
            conversation_type="direct_message",
            direct_agent_identity_id=self.agent_id,
            name="DM API Specialist",
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            server_id=self.server_id,
            preset_id=8,
            handle="api-specialist",
            display_name="API Specialist",
            lifecycle_state="active",
            created_by="owner-user",
            persistent_state=SimpleNamespace(active_session_id=uuid.uuid4()),
        )
        self.context_service.extract_trigger_body.return_value = (
            "Can you continue this work?"
        )
        self.context_service.build_trigger_envelope.return_value = AgentTriggerEnvelope(
            trigger_type="agent_dm",
            server_id=self.server_id,
            channel_id=self.channel_id,
            trigger_message_id=message.id,
            thread_root_message_id=message.id,
            target_agent_identity_id=self.agent_id,
            target_agent_handle="api-specialist",
            source_actor={"actor_type": "user", "user_id": "user-1"},
            handoff={
                "dedupe_key": f"channel-trigger:{message.id}:{self.agent_id}",
            },
        )
        self.task_service.enqueue_task.return_value = TaskEnqueueResponse(
            session_id=agent.persistent_state.active_session_id,
            accepted_type="queued_query",
            queue_item_id=uuid.uuid4(),
            status="queued",
            queued_query_count=1,
        )

        with patch(
            "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
            return_value=agent,
        ):
            results = self.service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        self.assertEqual(len(results), 1)
        _, _, request = self.task_service.enqueue_task.call_args.args
        self.assertEqual(request.session_id, agent.persistent_state.active_session_id)
        self.assertEqual(request.prompt, "Can you continue this work?")
        self.assertEqual(request.config.trigger_type, "agent_dm")
        self.assertEqual(request.config.trigger_context.trigger_type, "agent_dm")


if __name__ == "__main__":
    unittest.main()
