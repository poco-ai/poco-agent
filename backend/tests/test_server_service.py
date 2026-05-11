import unittest
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.models.server import Server
from app.models.agent_identity import AgentIdentity
from app.models.server_channel import ServerChannel
from app.models.server_invite import ServerInvite
from app.models.user import User
from app.schemas.server import ServerCreateRequest
from app.schemas.server_channel import (
    DirectMessageCreateRequest,
    ServerChannelMemberAddRequest,
    ServerChannelCreateRequest,
    ServerChannelUpdateRequest,
)
from app.schemas.server_invite import (
    ServerInviteAcceptRequest,
    ServerInviteCreateRequest,
)
from app.services.server_channel_service import ServerChannelService
from app.services.server_invite_service import ServerInviteService
from app.services.server_service import ServerService


class ServerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def test_list_servers_creates_personal_server_and_private_system_channel(
        self,
    ) -> None:
        service = ServerService()
        personal_server = Server(
            id=uuid.uuid4(),
            name="Alice's Server",
            slug="personal-user-1",
            kind="personal",
            owner_user_id="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_service.ServerRepository.get_personal_by_owner",
                return_value=None,
            ) as get_personal_by_owner,
            patch(
                "app.services.server_service.ServerRepository.get_by_slug",
                return_value=None,
            ),
            patch(
                "app.services.server_service.ServerRepository.create",
                side_effect=lambda _db, server: server,
            ) as create_server,
            patch(
                "app.services.server_service.ServerMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.server_service.ServerChannelRepository.create"
            ) as create_channel,
            patch(
                "app.services.server_service.ServerChannelMemberRepository.create"
            ) as create_channel_member,
            patch(
                "app.services.server_service.ServerRepository.list_by_user",
                return_value=[personal_server],
            ),
        ):
            result = service.list_servers(self.db, self.user)

        get_personal_by_owner.assert_called_once_with(self.db, "user-1")
        create_server.assert_called_once()
        create_member.assert_called_once()
        create_channel.assert_called_once()
        default_channel = create_channel.call_args.args[1]
        self.assertEqual(default_channel.name, "Personal")
        self.assertEqual(default_channel.slug, "personal")
        self.assertEqual(default_channel.visibility, "private")
        self.assertEqual(default_channel.system_channel_type, "personal")
        self.assertEqual(default_channel.conversation_type, "channel")
        create_channel_member.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertEqual(result[0].kind, "personal")

    def test_create_shared_server_creates_owner_and_public_system_channel(
        self,
    ) -> None:
        service = ServerService()
        shared_server = Server(
            id=uuid.uuid4(),
            name="Poco Core",
            slug="poco-core",
            kind="shared",
            owner_user_id="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch.object(service, "ensure_personal_server"),
            patch(
                "app.services.server_service.ServerRepository.get_by_slug",
                return_value=None,
            ),
            patch(
                "app.services.server_service.ServerRepository.create",
                return_value=shared_server,
            ),
            patch(
                "app.services.server_service.ServerMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.server_service.ServerChannelRepository.create"
            ) as create_channel,
            patch(
                "app.services.server_service.ServerChannelMemberRepository.create"
            ) as create_channel_member,
        ):
            result = service.create_server(
                self.db,
                self.user,
                ServerCreateRequest(name="Poco Core"),
            )

        create_member.assert_called_once()
        create_channel.assert_called_once()
        default_channel = create_channel.call_args.args[1]
        self.assertEqual(default_channel.name, "Public")
        self.assertEqual(default_channel.slug, "public")
        self.assertEqual(default_channel.visibility, "public")
        self.assertEqual(default_channel.system_channel_type, "public")
        self.assertEqual(default_channel.conversation_type, "channel")
        create_channel_member.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertEqual(result.kind, "shared")


class ServerChannelServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.server = Server(
            id=uuid.uuid4(),
            name="Poco Core",
            slug="poco-core",
            kind="shared",
            owner_user_id="user-1",
        )

    def test_member_can_create_channel_inside_server(self) -> None:
        service = ServerChannelService()

        with (
            patch(
                "app.services.server_channel_service.require_server_member",
                return_value=MagicMock(status="active", role="member"),
            ),
            patch(
                "app.services.server_channel_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_server_slug",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.create"
            ) as create_channel,
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.create"
            ) as create_member,
        ):

            def build_channel(_db, channel):
                channel.id = uuid.uuid4()
                channel.created_at = datetime.now(UTC)
                channel.updated_at = datetime.now(UTC)
                return channel

            create_channel.side_effect = build_channel

            result = service.create_channel(
                self.db,
                self.user,
                self.server.id,
                ServerChannelCreateRequest(name="General", visibility="public"),
            )

        create_channel.assert_called_once()
        create_member.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertEqual(result.slug, "general")
        self.assertEqual(result.visibility, "public")

    def test_admin_can_archive_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="general",
            slug="general",
            conversation_type="channel",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
        ):
            result = service.archive_channel(
                self.db,
                self.user,
                self.server.id,
                channel.id,
            )

        self.db.commit.assert_called_once()
        self.assertIsNotNone(channel.archived_at)
        self.assertEqual(result.channel_id, channel.id)

    def test_admin_cannot_archive_system_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="Public",
            slug="public",
            conversation_type="channel",
            visibility="public",
            system_channel_type="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
        ):
            with self.assertRaises(AppException):
                service.archive_channel(
                    self.db,
                    self.user,
                    self.server.id,
                    channel.id,
                )

        self.db.commit.assert_not_called()

    def test_admin_can_update_channel_name_and_description(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="planning",
            slug="planning",
            description=None,
            conversation_type="channel",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_server_slug",
                return_value=None,
            ),
        ):
            result = service.update_channel(
                self.db,
                self.user,
                self.server.id,
                channel.id,
                ServerChannelUpdateRequest(
                    name="Roadmap",
                    description="Roadmap planning",
                ),
            )

        self.db.commit.assert_called_once()
        self.assertEqual(channel.name, "Roadmap")
        self.assertEqual(channel.slug, "roadmap")
        self.assertEqual(channel.description, "Roadmap planning")
        self.assertEqual(result.description, "Roadmap planning")

    def test_admin_cannot_update_system_channel_metadata(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="Public",
            slug="public",
            description=None,
            conversation_type="channel",
            visibility="public",
            system_channel_type="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
        ):
            with self.assertRaises(AppException):
                service.update_channel(
                    self.db,
                    self.user,
                    self.server.id,
                    channel.id,
                    ServerChannelUpdateRequest(
                        name="Renamed",
                        description="Should not change",
                    ),
                )

        self.db.commit.assert_not_called()

    def test_admin_can_delete_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="planning",
            slug="planning",
            conversation_type="channel",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.delete"
            ) as delete_channel,
        ):
            service.delete_channel(self.db, self.user, self.server.id, channel.id)

        delete_channel.assert_called_once_with(self.db, channel)
        self.db.commit.assert_called_once()

    def test_admin_cannot_delete_system_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="Public",
            slug="public",
            conversation_type="channel",
            visibility="public",
            system_channel_type="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.delete"
            ) as delete_channel,
        ):
            with self.assertRaises(AppException):
                service.delete_channel(self.db, self.user, self.server.id, channel.id)

        delete_channel.assert_not_called()
        self.db.commit.assert_not_called()

    def test_admin_can_add_active_server_member_to_private_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="planning",
            slug="planning",
            conversation_type="channel",
            visibility="private",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_channel_service.ServerMemberRepository.get_by_server_and_user",
                return_value=MagicMock(status="active"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.get_by_channel_and_user",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.server_channel_service.create_channel_event_message"
            ) as create_event,
            patch(
                "app.services.server_channel_service.list_user_public_profiles_by_id",
                return_value={},
            ),
        ):

            def build_member(_db, membership):
                now = datetime.now(UTC)
                membership.id = 1
                membership.joined_at = now
                membership.created_at = now
                membership.updated_at = now
                return membership

            create_member.side_effect = build_member

            result = service.add_channel_member(
                self.db,
                self.user,
                self.server.id,
                channel.id,
                ServerChannelMemberAddRequest(user_id="user-2"),
            )

        create_member.assert_called_once()
        create_event.assert_called_once()
        event_kwargs = create_event.call_args.kwargs
        self.assertEqual(event_kwargs["event_type"], "channel.member_joined")
        self.assertEqual(event_kwargs["target"].target_user_id, "user-2")
        self.db.commit.assert_called_once()
        self.assertEqual(result.user_id, "user-2")

    def test_member_can_join_public_channel_once_with_event(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="Public",
            slug="public",
            conversation_type="channel",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_member",
                return_value=MagicMock(status="active", role="member"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.get_by_channel_and_user",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.server_channel_service.create_channel_event_message"
            ) as create_event,
            patch(
                "app.services.server_channel_service.list_user_public_profiles_by_id",
                return_value={},
            ),
        ):

            def build_member(_db, membership):
                now = datetime.now(UTC)
                membership.id = 2
                membership.joined_at = now
                membership.created_at = now
                membership.updated_at = now
                return membership

            create_member.side_effect = build_member

            service.join_channel(self.db, self.user, self.server.id, channel.id)

        create_event.assert_called_once()
        self.assertEqual(create_event.call_args.kwargs["content"]["join_reason"], "self_join")

    def test_member_cannot_leave_system_channel(self) -> None:
        service = ServerChannelService()
        channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="Public",
            slug="public",
            conversation_type="channel",
            visibility="public",
            system_channel_type="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_member",
                return_value=MagicMock(status="active", role="member"),
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_id",
                return_value=channel,
            ),
        ):
            with self.assertRaises(AppException):
                service.leave_channel(self.db, self.user, self.server.id, channel.id)

        self.db.commit.assert_not_called()

    def test_member_can_create_direct_message_with_agent(self) -> None:
        service = ServerChannelService()
        agent_identity = AgentIdentity(
            id=uuid.uuid4(),
            server_id=self.server.id,
            preset_id=7,
            handle="backend-specialist",
            display_name="Backend Specialist",
            description=None,
            visual_key="preset-visual-02",
            visibility="server",
            lifecycle_state="active",
            created_by="user-1",
            updated_by="user-1",
        )

        with (
            patch(
                "app.services.server_channel_service.require_server_member",
                return_value=MagicMock(status="active", role="member"),
            ),
            patch(
                "app.services.server_channel_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_by_server_slug",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_service.AgentIdentityRepository.get_by_id",
                return_value=agent_identity,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.get_direct_message",
                return_value=None,
            ),
            patch(
                "app.services.server_channel_service.ServerChannelRepository.create"
            ) as create_channel,
            patch(
                "app.services.server_channel_service.ServerChannelMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.server_channel_service.ServerChannelAgentMemberRepository.create"
            ) as create_agent_member,
        ):
            created_channel = None

            def build_channel(_db, channel):
                nonlocal created_channel
                created_channel = channel
                channel.created_at = datetime.now(UTC)
                channel.updated_at = datetime.now(UTC)
                return channel

            def flush_side_effect():
                assert created_channel is not None
                created_channel.id = uuid.uuid4()

            def build_agent_member(_db, membership):
                self.assertIsNotNone(membership.channel_id)
                return membership

            create_channel.side_effect = build_channel
            self.db.flush.side_effect = flush_side_effect
            create_agent_member.side_effect = build_agent_member

            result = service.create_direct_message(
                self.db,
                self.user,
                self.server.id,
                DirectMessageCreateRequest(target_agent_identity_id=agent_identity.id),
            )

        create_channel.assert_called_once()
        self.db.flush.assert_called_once()
        create_member.assert_called_once()
        create_agent_member.assert_called_once()
        created_channel = create_channel.call_args.args[1]
        self.assertEqual(created_channel.conversation_type, "direct_message")
        self.assertEqual(result.conversation_type, "direct_message")


class ServerInviteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-2",
            primary_email="bob@example.com",
            display_name="Bob",
            avatar_url=None,
            status="active",
        )
        self.server = Server(
            id=uuid.uuid4(),
            name="Poco Core",
            slug="poco-core",
            kind="shared",
            owner_user_id="user-1",
        )

    def test_create_invite_reuses_stable_key_for_server_and_creator(self) -> None:
        service = ServerInviteService()
        existing = ServerInvite(
            id=uuid.uuid4(),
            server_id=self.server.id,
            token="existing-token",
            role="member",
            expires_at=datetime.now(UTC) + timedelta(days=1),
            created_by=self.user.id,
            max_uses=1,
            used_count=1,
            revoked_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_invite_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.server_invite_service.require_server_admin",
                return_value=MagicMock(status="active", role="admin"),
            ),
            patch(
                "app.services.server_invite_service.ServerInviteRepository.get_by_server_and_creator",
                return_value=existing,
            ) as get_by_server_and_creator,
            patch(
                "app.services.server_invite_service.ServerInviteRepository.create"
            ) as create_invite,
        ):
            result = service.create_invite(
                self.db,
                self.user,
                self.server.id,
                ServerInviteCreateRequest(
                    role="admin",
                    expires_in_days=14,
                    max_uses=20,
                ),
            )

        get_by_server_and_creator.assert_called_once_with(
            self.db,
            self.server.id,
            self.user.id,
        )
        create_invite.assert_not_called()
        self.assertEqual(existing.role, "admin")
        self.assertEqual(existing.max_uses, 20)
        self.assertEqual(existing.used_count, 0)
        self.assertIsNone(existing.revoked_at)
        self.db.commit.assert_called_once()
        self.assertEqual(result.invite_id, existing.id)

    def test_accept_invite_creates_server_membership_and_public_channel_membership(
        self,
    ) -> None:
        service = ServerInviteService()
        invite = ServerInvite(
            id=uuid.uuid4(),
            server_id=self.server.id,
            token="invite-token",
            role="member",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by="user-1",
            max_uses=1,
            used_count=0,
            revoked_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.server_invite_service.ServerInviteRepository.get_by_token",
                return_value=invite,
            ),
            patch(
                "app.services.server_invite_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.server_invite_service.ServerMemberRepository.get_by_server_and_user",
                return_value=None,
            ),
            patch(
                "app.services.server_invite_service.ServerMemberRepository.create"
            ) as create_membership,
            patch(
                "app.services.server_invite_service.ServerChannelRepository.get_system_channel",
                return_value=ServerChannel(
                    id=uuid.uuid4(),
                    server_id=self.server.id,
                    name="Public",
                    slug="public",
                    visibility="public",
                    system_channel_type="public",
                    created_by="user-1",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                ),
            ),
            patch(
                "app.services.server_invite_service.ServerChannelMemberRepository.get_by_channel_and_user",
                return_value=None,
            ),
            patch(
                "app.services.server_invite_service.ServerChannelMemberRepository.create"
            ) as create_channel_member,
            patch(
                "app.services.server_invite_service.create_channel_event_message"
            ) as create_event,
        ):

            def build_membership(_db, membership):
                now = datetime.now(UTC)
                membership.id = 1
                membership.joined_at = now
                membership.created_at = now
                membership.updated_at = now
                return membership

            create_membership.side_effect = build_membership

            result = service.accept_invite(
                self.db,
                self.user,
                ServerInviteAcceptRequest(token="invite-token"),
            )

        create_membership.assert_called_once()
        create_channel_member.assert_called_once()
        create_event.assert_called_once()
        self.assertEqual(create_event.call_args.kwargs["event_type"], "channel.member_joined")
        self.assertEqual(create_event.call_args.kwargs["content"]["join_reason"], "server_invite")
        self.assertEqual(invite.used_count, 1)
        self.db.commit.assert_called_once()
        self.assertEqual(result.server_id, self.server.id)
        self.assertEqual(result.user_id, "user-2")


if __name__ == "__main__":
    unittest.main()
