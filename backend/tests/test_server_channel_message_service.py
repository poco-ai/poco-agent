import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.user import User
from app.schemas.input_file import InputFile
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

    def test_send_message_materializes_confirmed_draft_attachments(self) -> None:
        service = ServerChannelMessageService()
        artifact_id = uuid.uuid4()
        published_artifact = type(
            "Artifact",
            (),
            {
                "id": artifact_id,
                "display_name": "diagram.png",
                "logical_path": "/Uploads/diagram.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "source_kind": "user_upload",
                "object_key": "channel-artifacts/server/channel/Uploads/artifact/file",
            },
        )()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service."
                "ChannelArtifactService.publish_input_file_attachment",
                return_value=published_artifact,
            ) as publish_attachment,
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
                        "text": "please review #diagram.png",
                        "attachments": [
                            {
                                "id": "draft-1",
                                "type": "file",
                                "name": "diagram.png",
                                "source": "attachments/user-1/draft-1/file",
                                "size": 128,
                                "content_type": "image/png",
                            }
                        ],
                    },
                    text_preview="please review #diagram.png",
                ),
            )

        publish_attachment.assert_called_once()
        published_input = publish_attachment.call_args.kwargs["input_file"]
        self.assertIsInstance(published_input, InputFile)
        self.assertEqual(published_input.name, "diagram.png")

        created = create_message.call_args.args[1]
        self.assertEqual(
            created.content["attachments"][0]["path"], "/Uploads/diagram.png"
        )
        self.assertEqual(
            created.content["entities"][0]["target_id"],
            str(artifact_id),
        )
        self.assertEqual(
            created.content["entities"][0]["inserted_text"],
            "#diagram.png",
        )
        self.assertEqual(result.content["attachments"], created.content["attachments"])

    def test_send_message_prefers_draft_attachment_over_stale_artifact_entity(
        self,
    ) -> None:
        service = ServerChannelMessageService()
        stale_artifact_id = uuid.uuid4()
        published_artifact_id = uuid.uuid4()
        published_artifact = type(
            "Artifact",
            (),
            {
                "id": published_artifact_id,
                "display_name": "diagram.png",
                "logical_path": "/Uploads/diagram.png",
                "mime_type": "image/png",
                "size_bytes": 128,
                "source_kind": "user_upload",
                "object_key": "channel-artifacts/server/channel/Uploads/artifact/file",
            },
        )()

        def get_artifact(_db, *, channel_id, artifact_id):
            self.assertEqual(channel_id, self.channel.id)
            if artifact_id == published_artifact_id:
                return published_artifact
            return None

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service."
                "ChannelArtifactService.publish_input_file_attachment",
                return_value=published_artifact,
            ),
            patch(
                "app.services.server_channel_message_service."
                "ChannelArtifactRepository.get_by_channel_and_id",
                side_effect=get_artifact,
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
                        "text": "hi @jimi review #diagram.png",
                        "attachments": [
                            {
                                "id": "draft-1",
                                "type": "file",
                                "name": "diagram.png",
                                "source": "attachments/user-1/draft-1/file",
                                "size": 128,
                                "content_type": "image/png",
                            }
                        ],
                        "entities": [
                            {
                                "id": "stale-artifact-reference",
                                "kind": "artifact",
                                "action": "reference",
                                "targetId": str(stale_artifact_id),
                                "displayText": "diagram.png",
                                "insertedText": "#diagram.png",
                            }
                        ],
                    },
                    text_preview="hi @jimi review #diagram.png",
                ),
            )

        created = create_message.call_args.args[1]
        self.assertEqual(len(created.content["entities"]), 1)
        self.assertEqual(
            created.content["entities"][0]["target_id"],
            str(published_artifact_id),
        )
        self.assertEqual(result.content["entities"], created.content["entities"])

    def test_send_message_skips_unconfirmed_draft_attachments(self) -> None:
        service = ServerChannelMessageService()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service."
                "ChannelArtifactService.publish_input_file_attachment",
            ) as publish_attachment,
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

            service.send_message(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelMessageCreateRequest(
                    content={
                        "text": "please review this image",
                        "attachments": [
                            {
                                "id": "draft-1",
                                "type": "file",
                                "name": "diagram.png",
                                "source": "attachments/user-1/draft-1/file",
                                "size": 128,
                                "content_type": "image/png",
                            }
                        ],
                    },
                    text_preview="please review this image",
                ),
            )

        publish_attachment.assert_not_called()
        created = create_message.call_args.args[1]
        self.assertEqual(created.content["attachments"], [])
        self.assertNotIn("entities", created.content)

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

    def test_send_message_omits_entities_key_when_only_empty_attachments(self) -> None:
        # Regression: the composer always sends `attachments: []`. A plain @-mention
        # reply must NOT gain an `entities` key, otherwise the trigger service treats
        # the (empty) entities as authoritative and skips the @handle text fallback.
        service = ServerChannelMessageService()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_message_service."
                "ServerChannelMessageRepository.create"
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

            service.send_message(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelMessageCreateRequest(
                    content={
                        "text": "please review @api-specialist",
                        "attachments": [],
                    },
                    text_preview="please review @api-specialist",
                ),
            )

        created = create_message.call_args.args[1]
        self.assertNotIn("entities", created.content)


if __name__ == "__main__":
    unittest.main()
