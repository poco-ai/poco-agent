import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.models.server_channel_message import ServerChannelMessage
from app.schemas.channel_runtime import (
    AgentChannelCollaborationRequest,
    AgentChannelMessageReadRequest,
)
from app.schemas.task import TaskEnqueueResponse
from app.services.channel_runtime_service import ChannelRuntimeService


class ChannelRuntimeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.trigger_message_id = uuid.uuid4()
        self.thread_root_message_id = uuid.uuid4()
        self.scope = SimpleNamespace(
            session_id=self.session_id,
            user_id="agent-owner",
            server_id=self.server_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            agent_handle="reviewer",
            agent_label="Reviewer",
            agent_preset_id=8,
            trigger_message_id=self.trigger_message_id,
            thread_root_message_id=self.thread_root_message_id,
            handoff_depth=1,
        )
        self.task_service = MagicMock()
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
        self.service = ChannelRuntimeService(
            task_service=self.task_service,
            persistent_runtime_service=self.runtime_service,
        )

    def _message(
        self,
        message_id: uuid.UUID,
        *,
        channel_id: uuid.UUID | None = None,
        text: str = "hello",
        thread_root_message_id: uuid.UUID | None = None,
    ) -> ServerChannelMessage:
        now = datetime.now(UTC)
        return ServerChannelMessage(
            id=message_id,
            channel_id=channel_id or self.channel_id,
            author_user_id="user-1",
            message_type="user",
            content={"text": text},
            text_preview=text,
            thread_root_message_id=thread_root_message_id,
            created_at=now,
            updated_at=now,
        )

    def test_read_messages_rejects_cross_channel_message(self) -> None:
        message_id = uuid.uuid4()
        other_channel_id = uuid.uuid4()
        message = self._message(message_id, channel_id=other_channel_id)

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.get_by_id",
                return_value=message,
            ),
        ):
            with self.assertRaises(AppException) as context:
                self.service.read_messages(
                    self.db,
                    session_id=self.session_id,
                    request=AgentChannelMessageReadRequest(message_ids=[message_id]),
                )

        self.assertIn("Message not found", str(context.exception))

    def test_read_messages_returns_full_content_and_reactions(self) -> None:
        message_id = uuid.uuid4()
        message = self._message(message_id, text="Full message body")
        reaction_group = SimpleNamespace(emoji="👍", count=1)

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.get_by_id",
                return_value=message,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.count_replies_by_roots",
                return_value={message_id: 2},
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageReactionService.list_grouped_by_messages",
                return_value={message_id: [reaction_group]},
            ),
        ):
            result = self.service.read_messages(
                self.db,
                session_id=self.session_id,
                request=AgentChannelMessageReadRequest(message_ids=[message_id]),
            )

        self.assertEqual(result.messages[0].message_id, message_id)
        self.assertEqual(result.messages[0].content["text"], "Full message body")
        self.assertEqual(result.messages[0].reply_count, 2)
        self.assertEqual(result.messages[0].reactions[0], reaction_group)

    def test_read_messages_without_selector_returns_channel_timeline(self) -> None:
        message_id = uuid.uuid4()
        message = self._message(message_id, text="Latest channel message")

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.list_by_channel",
                return_value=[message],
            ) as list_by_channel,
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.count_replies_by_roots",
                return_value={},
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageReactionService.list_grouped_by_messages",
                return_value={},
            ),
        ):
            result = self.service.read_messages(
                self.db,
                session_id=self.session_id,
                request=AgentChannelMessageReadRequest(limit=20),
            )

        list_by_channel.assert_called_once_with(
            self.db,
            self.channel_id,
            before_message_id=None,
            limit=20,
        )
        self.assertEqual([item.message_id for item in result.messages], [message_id])

    def test_read_messages_can_read_all_channel_timeline_messages(self) -> None:
        message_id = uuid.uuid4()
        message = self._message(message_id, text="Timeline message")

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.list_all_by_channel",
                return_value=[message],
            ) as list_all_by_channel,
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.count_replies_by_roots",
                return_value={},
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageReactionService.list_grouped_by_messages",
                return_value={},
            ),
        ):
            result = self.service.read_messages(
                self.db,
                session_id=self.session_id,
                request=AgentChannelMessageReadRequest(read_all=True),
            )

        list_all_by_channel.assert_called_once_with(
            self.db,
            self.channel_id,
            limit=None,
        )
        self.assertEqual([item.message_id for item in result.messages], [message_id])

    def test_read_messages_can_page_before_anchor_message(self) -> None:
        anchor_id = uuid.uuid4()
        older_id = uuid.uuid4()
        anchor = self._message(anchor_id, text="anchor")
        older = self._message(older_id, text="older")

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.get_by_id",
                return_value=anchor,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.list_from_anchor",
                return_value=[older],
            ) as list_from_anchor,
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.count_replies_by_roots",
                return_value={},
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageReactionService.list_grouped_by_messages",
                return_value={},
            ),
        ):
            result = self.service.read_messages(
                self.db,
                session_id=self.session_id,
                request=AgentChannelMessageReadRequest(
                    anchor_message_id=anchor_id,
                    direction="before",
                    limit=20,
                ),
            )

        list_from_anchor.assert_called_once_with(
            self.db,
            self.channel_id,
            anchor_message=anchor,
            direction="before",
            limit=19,
        )
        self.assertEqual(
            [item.message_id for item in result.messages],
            [anchor_id, older_id],
        )

    def test_read_messages_can_page_after_anchor_message(self) -> None:
        anchor_id = uuid.uuid4()
        newer_id = uuid.uuid4()
        anchor = self._message(anchor_id, text="anchor")
        newer = self._message(newer_id, text="newer")

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.get_by_id",
                return_value=anchor,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.list_from_anchor",
                return_value=[newer],
            ) as list_from_anchor,
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.count_replies_by_roots",
                return_value={},
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageReactionService.list_grouped_by_messages",
                return_value={},
            ),
        ):
            result = self.service.read_messages(
                self.db,
                session_id=self.session_id,
                request=AgentChannelMessageReadRequest(
                    anchor_message_id=anchor_id,
                    direction="after",
                    limit=20,
                ),
            )

        list_from_anchor.assert_called_once_with(
            self.db,
            self.channel_id,
            anchor_message=anchor,
            direction="after",
            limit=19,
        )
        self.assertEqual(
            [item.message_id for item in result.messages],
            [anchor_id, newer_id],
        )

    def test_list_agents_returns_active_channel_agents(self) -> None:
        target_agent_id = uuid.uuid4()
        memberships = [
            SimpleNamespace(agent_identity_id=target_agent_id, status="active"),
            SimpleNamespace(agent_identity_id=uuid.uuid4(), status="removed"),
        ]
        target_agent = SimpleNamespace(
            id=target_agent_id,
            server_id=self.server_id,
            handle="api",
            display_name="API",
            description="API owner",
            visual_key="blue",
            lifecycle_state="active",
        )

        def get_agent(_db, agent_id):
            return target_agent if agent_id == target_agent_id else None

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelAgentMemberRepository.list_by_channel",
                return_value=memberships,
            ),
            patch(
                "app.services.channel_runtime_service.AgentIdentityRepository.get_by_id",
                side_effect=get_agent,
            ),
        ):
            result = self.service.list_agents(self.db, session_id=self.session_id)

        self.assertEqual(len(result.agents), 1)
        self.assertEqual(result.agents[0].handle, "api")
        self.assertEqual(result.agents[0].description, "API owner")

    def test_request_collaboration_rejects_self_target(self) -> None:
        with patch.object(
            self.service._scope_service,
            "resolve_scope",
            return_value=self.scope,
        ):
            with self.assertRaises(AppException) as context:
                self.service.request_collaboration(
                    self.db,
                    session_id=self.session_id,
                    request=AgentChannelCollaborationRequest(
                        agent_handle="reviewer",
                        request_text="Please continue this.",
                    ),
                )

        self.assertIn("cannot target the current agent", str(context.exception))

    def test_request_collaboration_rejects_max_handoff_depth(self) -> None:
        scope = SimpleNamespace(**{**self.scope.__dict__, "handoff_depth": 2})

        with patch.object(
            self.service._scope_service,
            "resolve_scope",
            return_value=scope,
        ):
            with self.assertRaises(AppException) as context:
                self.service.request_collaboration(
                    self.db,
                    session_id=self.session_id,
                    request=AgentChannelCollaborationRequest(
                        agent_handle="api",
                        request_text="Please continue this.",
                    ),
                )

        self.assertIn("hop depth", str(context.exception))

    def test_request_collaboration_enqueues_target_agent_with_trigger_context(
        self,
    ) -> None:
        target_agent_id = uuid.uuid4()
        active_session_id = uuid.uuid4()
        target_agent = SimpleNamespace(
            id=target_agent_id,
            server_id=self.server_id,
            handle="api",
            display_name="API",
            preset_id=10,
            created_by="api-owner",
            lifecycle_state="active",
            persistent_state=SimpleNamespace(active_session_id=active_session_id),
        )
        membership = SimpleNamespace(status="active")
        self.task_service.enqueue_task.return_value = TaskEnqueueResponse(
            session_id=active_session_id,
            accepted_type="run",
            run_id=uuid.uuid4(),
            status="queued",
            queued_query_count=0,
        )

        with (
            patch.object(
                self.service._scope_service,
                "resolve_scope",
                return_value=self.scope,
            ),
            patch(
                "app.services.channel_runtime_service.AgentIdentityRepository.get_by_server_and_handle",
                return_value=target_agent,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=membership,
            ),
            patch(
                "app.services.channel_runtime_service.ServerChannelMessageRepository.get_by_id",
                return_value=SimpleNamespace(
                    id=self.trigger_message_id,
                    thread_root_message_id=None,
                ),
            ),
            patch(
                "app.services.server_agent_trigger_service.ServerAgentTriggerService._create_execution_placeholder"
            ) as create_placeholder,
        ):
            result = self.service.request_collaboration(
                self.db,
                session_id=self.session_id,
                request=AgentChannelCollaborationRequest(
                    agent_handle="api",
                    request_text="Please review the auth-specific part.",
                    reference_message_ids=[self.trigger_message_id],
                    mode="consult",
                ),
            )

        self.task_service.enqueue_task.assert_called_once()
        _, owner_user_id, enqueue_request = (
            self.task_service.enqueue_task.call_args.args
        )
        self.assertEqual(owner_user_id, "api-owner")
        self.assertEqual(
            enqueue_request.prompt, "Please review the auth-specific part."
        )
        self.assertEqual(enqueue_request.session_id, active_session_id)
        self.assertEqual(enqueue_request.config.trigger_type, "agent_collaboration")
        self.assertEqual(
            enqueue_request.config.trigger_context.trigger_type, "agent_collaboration"
        )
        self.assertEqual(result.status, "queued")
        create_placeholder.assert_called_once()


if __name__ == "__main__":
    unittest.main()
