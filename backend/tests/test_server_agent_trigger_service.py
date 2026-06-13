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
        self.runtime_service = MagicMock()
        self.runtime_service.ensure_server_agent_runtime.side_effect = (
            lambda _db, agent_identity: SimpleNamespace(
                runtime_key=f"server_agent:{agent_identity.id}",
                session_id=getattr(
                    getattr(agent_identity, "persistent_state", None),
                    "active_session_id",
                    None,
                ),
            )
        )
        self.service = ServerAgentTriggerService(
            task_service=self.task_service,
            shared_context_service=self.context_service,
            persistent_runtime_service=self.runtime_service,
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

    def test_structured_agent_entity_ignores_extra_regex_mentions(self) -> None:
        other_agent_id = uuid.uuid4()
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="@api-specialist and @other-agent",
            content={
                "text": "@api-specialist and @other-agent",
                "entities": [
                    {
                        "kind": "agent",
                        "action": "trigger",
                        "target_id": str(self.agent_id),
                    },
                    {
                        "kind": "artifact",
                        "action": "reference",
                        "target_id": str(uuid.uuid4()),
                    },
                ],
            },
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
            "@api-specialist and @other-agent"
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

        def get_agent(_db, agent_id):
            if agent_id == self.agent_id:
                return agent
            if agent_id == other_agent_id:
                return SimpleNamespace(
                    id=other_agent_id,
                    handle="other-agent",
                    lifecycle_state="active",
                    removed_at=None,
                )
            return None

        with (
            patch(
                "app.services.server_agent_trigger_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=membership,
            ) as get_membership,
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                side_effect=get_agent,
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
        get_membership.assert_called_once_with(self.db, self.channel_id, self.agent_id)
        _, _, request = self.task_service.enqueue_task.call_args.args
        self.assertEqual(request.config.agent_identity_id, self.agent_id)
        self.assertEqual(request.config.trigger_type, "channel_mention")

    def test_structured_references_are_passed_to_trigger_envelope(self) -> None:
        artifact_id = uuid.uuid4()
        task_id = uuid.uuid4()
        referenced_message_id = uuid.uuid4()
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="@api-specialist check refs",
            content={
                "text": "@api-specialist check refs",
                "entities": [
                    {
                        "kind": "agent",
                        "action": "trigger",
                        "target_id": str(self.agent_id),
                    },
                    {
                        "kind": "artifact",
                        "action": "reference",
                        "target_id": str(artifact_id),
                    },
                    {
                        "kind": "task",
                        "action": "reference",
                        "target_id": str(task_id),
                    },
                    {
                        "kind": "thread",
                        "action": "reference",
                        "target_id": str(referenced_message_id),
                    },
                    {
                        "kind": "user",
                        "action": "mention",
                        "target_id": "user-2",
                    },
                    {
                        "kind": "artifact",
                        "action": "reference",
                        "target_id": str(artifact_id),
                    },
                ],
            },
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
            "@api-specialist check refs"
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
                "app.services.server_agent_trigger_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=membership,
            ),
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
        ):
            self.service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        kwargs = self.context_service.build_trigger_envelope.call_args.kwargs
        references = kwargs["references"]
        self.assertEqual(references.message_ids, [message.id, referenced_message_id])
        self.assertEqual(references.artifact_ids, [artifact_id])
        self.assertEqual(references.task_ids, [task_id])

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

    def test_text_mention_triggers_when_entities_contain_no_agent(self) -> None:
        # Regression: a reply can carry an `entities` array (e.g. a file-reference
        # produced by the composer) that has no agent-trigger entity, while the text
        # mentions an agent. The @handle text fallback must still trigger the agent
        # instead of being skipped just because an `entities` key is present.
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="@api-specialist please review",
            content={
                "text": "@api-specialist please review",
                "entities": [
                    {
                        "kind": "artifact",
                        "action": "reference",
                        "target_id": str(uuid.uuid4()),
                    }
                ],
            },
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
            "@api-specialist please review"
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
                "app.services.server_agent_trigger_service."
                "ServerChannelAgentMemberRepository.list_by_channel",
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
        self.task_service.enqueue_task.assert_called_once()
        _, _, request = self.task_service.enqueue_task.call_args.args
        self.assertEqual(request.config.agent_identity_id, self.agent_id)


if __name__ == "__main__":
    unittest.main()
