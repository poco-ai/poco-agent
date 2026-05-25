import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.user import User
from app.schemas.agent_trigger import TriggerReferences
from app.services.channel_shared_context_service import ChannelSharedContextService


class ChannelSharedContextServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = ChannelSharedContextService()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.message_id = uuid.uuid4()
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def test_build_trigger_envelope_uses_message_and_agent_indexes(self) -> None:
        message = SimpleNamespace(
            id=self.message_id,
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist",
            content={"text": "Please review @api-specialist"},
            thread_root_message_id=None,
        )
        agent_id = uuid.uuid4()

        envelope = self.service.build_trigger_envelope(
            server_id=self.server_id,
            channel_id=self.channel_id,
            message=message,
            current_user=self.current_user,
            target_agent_identity_id=agent_id,
            target_agent_handle="api-specialist",
            trigger_type="channel_mention",
        )

        payload = envelope.model_dump(mode="json")
        self.assertEqual(payload["trigger_type"], "channel_mention")
        self.assertEqual(payload["trigger_message_id"], str(self.message_id))
        self.assertEqual(payload["thread_root_message_id"], str(self.message_id))
        self.assertEqual(payload["target_agent_identity_id"], str(agent_id))
        self.assertEqual(payload["source_actor"]["user_id"], "user-1")
        self.assertEqual(
            payload["handoff"]["dedupe_key"],
            f"channel-trigger:{self.message_id}:{agent_id}",
        )

    def test_build_trigger_envelope_uses_explicit_references(self) -> None:
        message = SimpleNamespace(
            id=self.message_id,
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist #design.md",
            content={"text": "Please review @api-specialist #design.md"},
            thread_root_message_id=None,
        )
        agent_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        task_id = uuid.uuid4()
        references = TriggerReferences(
            message_ids=[self.message_id],
            artifact_ids=[artifact_id],
            task_ids=[task_id],
        )

        envelope = self.service.build_trigger_envelope(
            server_id=self.server_id,
            channel_id=self.channel_id,
            message=message,
            current_user=self.current_user,
            target_agent_identity_id=agent_id,
            target_agent_handle="api-specialist",
            trigger_type="channel_mention",
            references=references,
        )

        self.assertEqual(envelope.references.message_ids, [self.message_id])
        self.assertEqual(envelope.references.artifact_ids, [artifact_id])
        self.assertEqual(envelope.references.task_ids, [task_id])

    def test_extract_trigger_body_prefers_full_content_over_preview(self) -> None:
        full_text = ("Complete @jimi summary " + ("details " * 120)).strip()
        truncated_preview = "Complete @jimi summary details details"
        message = SimpleNamespace(
            id=self.message_id,
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview=truncated_preview,
            content={"text": full_text},
            thread_root_message_id=None,
        )

        body = self.service.extract_trigger_body(message)

        self.assertEqual(body, full_text)

    def test_build_legacy_prompt_for_sdk_uses_lightweight_context_index(self) -> None:
        message = SimpleNamespace(
            id=self.message_id,
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist",
            content={"text": "Please review @api-specialist"},
            thread_root_message_id=None,
        )
        recent_messages = [
            SimpleNamespace(
                id=uuid.uuid4(),
                channel_id=self.channel_id,
                author_user_id="user-2",
                author_user=SimpleNamespace(display_name="Bob", user_id="user-2"),
                text_preview="Rate limit plan updated",
                content={"text": "Rate limit plan updated"},
                message_type="user",
            )
        ]
        artifacts = [
            SimpleNamespace(
                id=uuid.uuid4(),
                display_name="rate-limit-plan.md",
                logical_path="/plans/rate-limit-plan.md",
                mime_type="text/markdown",
                size_bytes=120,
                object_key="objects/rate-limit-plan.md",
            )
        ]

        with (
            patch(
                "app.services.channel_shared_context_service."
                "ServerChannelMessageRepository.list_by_channel",
                return_value=recent_messages,
            ),
            patch(
                "app.services.channel_shared_context_service."
                "ChannelArtifactRepository.list_by_channel",
                return_value=artifacts,
            ),
            patch.object(
                self.service._storage,
                "get_text",
                return_value="# Plan\nUse per-user rate limits.",
            ),
        ):
            prompt = self.service.build_message_trigger_prompt(
                self.db,
                server_id=self.server_id,
                channel_id=self.channel_id,
                message=message,
                current_user=self.current_user,
                agent_display_name="API Specialist",
            )

        self.assertIn("API Specialist", prompt)
        self.assertIn("Please review @api-specialist", prompt)
        self.assertIn("Rate limit plan updated", prompt)
        self.assertIn("rate-limit-plan.md", prompt)
        self.assertIn("list_channel_artifacts", prompt)
        self.assertIn("read_channel_artifact", prompt)
        self.assertIn("not /workspace paths", prompt)
        self.assertIn("artifact_id:", prompt)
        self.assertNotIn("Use per-user rate limits.", prompt)

    def test_build_message_trigger_prompt_shows_trigger_body_once(self) -> None:
        full_text = ("Complete @jimi summary " + ("details " * 120)).strip()
        truncated_preview = "Complete @jimi summary details details"
        message = SimpleNamespace(
            id=self.message_id,
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview=truncated_preview,
            content={"text": full_text},
            thread_root_message_id=None,
        )
        recent_messages = [
            SimpleNamespace(
                id=uuid.uuid4(),
                channel_id=self.channel_id,
                author_user_id=None,
                author_user=None,
                text_preview=truncated_preview,
                content={"text": full_text},
                message_type="system",
            )
        ]

        with (
            patch(
                "app.services.channel_shared_context_service."
                "ServerChannelMessageRepository.list_by_channel",
                return_value=recent_messages,
            ),
            patch(
                "app.services.channel_shared_context_service."
                "ChannelArtifactRepository.list_by_channel",
                return_value=[],
            ),
            patch(
                "app.services.channel_shared_context_service."
                "ServerChannelMemberRepository.list_by_channel",
                return_value=[],
            ),
            patch(
                "app.services.channel_shared_context_service."
                "UserRepository.list_by_ids",
                return_value=[],
            ),
            patch(
                "app.services.channel_shared_context_service."
                "ServerChannelAgentMemberRepository.list_by_channel",
                return_value=[],
            ),
        ):
            prompt = self.service.build_message_trigger_prompt(
                self.db,
                server_id=self.server_id,
                channel_id=self.channel_id,
                message=message,
                current_user=self.current_user,
                agent_display_name="API Specialist",
            )

        self.assertIn(full_text, prompt)
        self.assertEqual(prompt.count(full_text), 1)


if __name__ == "__main__":
    unittest.main()
