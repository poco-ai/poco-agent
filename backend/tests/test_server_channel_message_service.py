import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.user import User
from app.schemas.server_channel_message import ServerChannelMessageCreateRequest
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_channel_message_service import ServerChannelMessageService


class ServerChannelMessageServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.server_id = uuid.uuid4()
        self.channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server_id,
            name="general",
            slug="general",
            visibility="public",
            created_by="user-1",
            archived_at=None,
        )

    def test_send_user_message_creates_channel_message(self) -> None:
        service = ServerChannelMessageService()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.create"
            ) as create_message,
            patch(
                "app.services.server_channel_message_service."
                "ServerAgentTriggerService.trigger_for_channel_message",
                return_value=[],
            ),
        ):

            def build_message(_db, message):
                now = datetime.now(UTC)
                message.id = uuid.uuid4()
                message.created_at = now
                message.updated_at = now
                return message

            create_message.side_effect = build_message

            result = service.send_message(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelMessageCreateRequest(
                    content={"text": "hello"},
                    text_preview="hello",
                ),
            )

        create_message.assert_called_once()
        created = create_message.call_args.args[1]
        self.assertEqual(created.message_type, "user")
        self.assertEqual(created.author_user_id, "user-1")
        self.assertIsNone(created.thread_root_message_id)
        self.db.commit.assert_called_once()
        self.assertEqual(result.text_preview, "hello")
        author_user = result.author_user
        assert author_user is not None
        self.assertEqual(author_user.user_id, "user-1")
        self.assertEqual(author_user.display_name, "Alice")

    def test_send_thread_reply_requires_existing_root_message(self) -> None:
        service = ServerChannelMessageService()
        root_message = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel.id,
            author_user_id="user-1",
            message_type="user",
            content={"text": "root"},
            text_preview="root",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.get_by_id",
                return_value=root_message,
            ),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.create"
            ) as create_message,
            patch(
                "app.services.server_channel_message_service."
                "ServerAgentTriggerService.trigger_for_channel_message",
                return_value=[],
            ),
        ):

            def build_message(_db, message):
                now = datetime.now(UTC)
                message.id = uuid.uuid4()
                message.created_at = now
                message.updated_at = now
                return message

            create_message.side_effect = build_message

            result = service.send_message(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelMessageCreateRequest(
                    content={"text": "reply"},
                    text_preview="reply",
                    thread_root_message_id=root_message.id,
                ),
            )

        created = create_message.call_args.args[1]
        self.assertEqual(created.thread_root_message_id, root_message.id)
        self.assertEqual(result.thread_root_message_id, root_message.id)
        author_user = result.author_user
        assert author_user is not None
        self.assertEqual(author_user.user_id, "user-1")

    def test_send_message_canonicalizes_agent_and_artifact_entities(self) -> None:
        service = ServerChannelMessageService()
        agent_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        agent = type(
            "Agent",
            (),
            {
                "id": agent_id,
                "server_id": self.server_id,
                "handle": "reviewer",
                "display_name": "Reviewer",
                "description": "Reviews changes",
                "visual_key": "blue",
                "lifecycle_state": "active",
                "removed_at": None,
            },
        )()
        agent_membership = type(
            "AgentMembership",
            (),
            {"agent_identity_id": agent_id, "status": "active"},
        )()
        artifact = type(
            "Artifact",
            (),
            {
                "id": artifact_id,
                "display_name": "design.md",
                "logical_path": "/docs/design.md",
                "mime_type": "text/markdown",
                "size_bytes": 42,
                "source_kind": "upload",
            },
        )()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service."
                "ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=agent_membership,
            ),
            patch(
                "app.services.server_channel_message_service."
                "AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.server_channel_message_service."
                "ChannelArtifactRepository.get_by_channel_and_id",
                return_value=artifact,
            ),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.create"
            ) as create_message,
            patch(
                "app.services.server_channel_message_service."
                "ServerAgentTriggerService.trigger_for_channel_message",
                return_value=[],
            ),
        ):

            def build_message(_db, message):
                now = datetime.now(UTC)
                message.id = uuid.uuid4()
                message.created_at = now
                message.updated_at = now
                return message

            create_message.side_effect = build_message

            result = service.send_message(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelMessageCreateRequest(
                    content={
                        "text": "@reviewer check #design.md",
                        "entities": [
                            {
                                "id": "entity-agent",
                                "kind": "agent",
                                "action": "trigger",
                                "targetId": str(agent_id),
                                "displayText": "Forged Label",
                                "insertedText": "@wrong",
                                "metadata": {"handle": "wrong"},
                            },
                            {
                                "id": "entity-artifact",
                                "kind": "artifact",
                                "action": "reference",
                                "targetId": str(artifact_id),
                                "displayText": "fake.md",
                                "insertedText": "#design.md",
                            },
                        ],
                    },
                    text_preview="@reviewer check #design.md",
                ),
            )

        created = create_message.call_args.args[1]
        entities = created.content["entities"]
        self.assertEqual(entities[0]["target_id"], str(agent_id))
        self.assertEqual(entities[0]["display_text"], "Reviewer")
        self.assertEqual(entities[0]["inserted_text"], "@reviewer")
        self.assertEqual(entities[0]["metadata"]["handle"], "reviewer")
        self.assertEqual(entities[1]["target_id"], str(artifact_id))
        self.assertEqual(entities[1]["display_text"], "design.md")
        self.assertEqual(entities[1]["metadata"]["logical_path"], "/docs/design.md")
        self.assertEqual(result.content["entities"], entities)

    def test_get_thread_returns_root_and_replies(self) -> None:
        service = ServerChannelMessageService()
        root = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel.id,
            author_user_id="user-1",
            message_type="user",
            content={"text": "root"},
            text_preview="root",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        reply = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel.id,
            author_user_id="user-2",
            message_type="user",
            content={"text": "reply"},
            text_preview="reply",
            thread_root_message_id=root.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.get_by_id",
                return_value=root,
            ),
            patch(
                "app.services.server_channel_message_service.ServerChannelMessageRepository.list_replies",
                return_value=[reply],
            ),
            patch(
                "app.services.server_channel_message_service.list_user_public_profiles_by_id",
                return_value={
                    "user-1": UserPublicProfileResponse(
                        user_id="user-1",
                        display_name="Alice",
                        avatar_url="https://example.com/alice.png",
                    ),
                    "user-2": UserPublicProfileResponse(
                        user_id="user-2",
                        display_name="Bob",
                        avatar_url="https://example.com/bob.png",
                    ),
                },
            ),
        ):
            result = service.get_thread(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                root.id,
            )

        self.assertEqual(result.root.message_id, root.id)
        self.assertEqual(result.replies[0].message_id, reply.id)
        root_author = result.root.author_user
        reply_author = result.replies[0].author_user
        assert root_author is not None
        assert reply_author is not None
        self.assertEqual(root_author.display_name, "Alice")
        self.assertEqual(reply_author.display_name, "Bob")


if __name__ == "__main__":
    unittest.main()
