import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_identity import AgentIdentity
from app.models.agent_persistent_state import AgentPersistentState
from app.models.server import Server
from app.models.server_channel import ServerChannel
from app.models.server_channel_agent_member import ServerChannelAgentMember
from app.models.user import User
from app.schemas.agent_identity import (
    AgentIdentityCreateRequest,
    ChannelAgentMemberCreateRequest,
)
from app.services.agent_identity_service import AgentIdentityService


class AgentIdentityServiceTests(unittest.TestCase):
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.channel = ServerChannel(
            id=uuid.uuid4(),
            server_id=self.server.id,
            name="backend",
            slug="backend",
            visibility="public",
            created_by="user-1",
            archived_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_create_agent_creates_identity_and_persistent_state(self) -> None:
        persistent_runtime_service = MagicMock()
        runtime_stub = SimpleNamespace(
            runtime_key="server_agent:test",
            lifecycle_state="sleeping",
            session_id=None,
            container_id=None,
            keepalive_until=None,
            last_stopped_at=None,
            last_stop_reason=None,
        )
        persistent_runtime_service.ensure_server_agent_runtime.return_value = (
            runtime_stub
        )
        persistent_runtime_service.get_runtime.return_value = None
        service = AgentIdentityService(
            persistent_runtime_service=persistent_runtime_service
        )
        preset = MagicMock(id=7, visual_key="preset-visual-02")

        with (
            patch(
                "app.services.agent_identity_service.require_server_admin",
                return_value=MagicMock(role="admin"),
            ),
            patch(
                "app.services.agent_identity_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.agent_identity_service.PresetRepository.get_visible_by_id",
                return_value=preset,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_server_and_handle",
                return_value=None,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_server_and_display_name",
                return_value=None,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.create"
            ) as create_agent,
            patch(
                "app.services.agent_identity_service.AgentPersistentStateRepository.create"
            ) as create_state,
            patch(
                "app.services.agent_identity_service.ensure_agent_state_bootstrap"
            ) as ensure_bootstrap,
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_id"
            ) as get_by_id,
        ):
            now = datetime.now(UTC)

            def build_agent(_db, agent_identity):
                agent_identity.id = uuid.uuid4()
                agent_identity.created_at = now
                agent_identity.updated_at = now
                return agent_identity

            create_agent.side_effect = build_agent
            get_by_id.side_effect = lambda _db, _id: create_agent.call_args.args[1]

            result = service.create_agent(
                self.db,
                self.user,
                self.server.id,
                AgentIdentityCreateRequest(
                    display_name="Backend Specialist",
                    preset_id=7,
                ),
            )

        create_agent.assert_called_once()
        create_state.assert_called_once()
        ensure_bootstrap.assert_called_once()
        created = create_agent.call_args.args[1]
        self.assertEqual(created.display_name, "Backend Specialist")
        self.assertEqual(created.preset_id, 7)
        self.assertTrue(created.handle.startswith("backend-specialist"))
        self.assertEqual(result.display_name, "Backend Specialist")
        self.db.commit.assert_called_once()

    def test_create_agent_rejects_duplicate_display_name(self) -> None:
        service = AgentIdentityService(persistent_runtime_service=MagicMock())
        preset = MagicMock(id=7, visual_key="preset-visual-02")
        existing_agent = AgentIdentity(
            id=uuid.uuid4(),
            server_id=self.server.id,
            preset_id=7,
            handle="reviewer",
            display_name="Reviewer",
            description=None,
            visual_key="preset-visual-02",
            visibility="server",
            lifecycle_state="active",
            created_by="user-1",
            updated_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.agent_identity_service.require_server_admin",
                return_value=MagicMock(role="admin"),
            ),
            patch(
                "app.services.agent_identity_service.ServerRepository.get_by_id",
                return_value=self.server,
            ),
            patch(
                "app.services.agent_identity_service.PresetRepository.get_visible_by_id",
                return_value=preset,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_server_and_display_name",
                return_value=existing_agent,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.create"
            ) as create_agent,
        ):
            with self.assertRaises(AppException) as context:
                service.create_agent(
                    self.db,
                    self.user,
                    self.server.id,
                    AgentIdentityCreateRequest(
                        display_name="Reviewer",
                        preset_id=7,
                    ),
                )

        self.assertEqual(context.exception.error_code, ErrorCode.BAD_REQUEST)
        create_agent.assert_not_called()
        self.db.commit.assert_not_called()

    def test_add_agent_to_channel_creates_membership(self) -> None:
        service = AgentIdentityService(persistent_runtime_service=MagicMock())
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.agent_identity_service.require_server_admin",
                return_value=MagicMock(role="admin"),
            ) as require_admin,
            patch(
                "app.services.agent_identity_service.ServerChannelRepository.get_by_id",
                return_value=self.channel,
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_id",
                return_value=agent_identity,
            ),
            patch(
                "app.services.agent_identity_service.ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=None,
            ),
            patch(
                "app.services.agent_identity_service.ServerChannelAgentMemberRepository.create"
            ) as create_membership,
            patch(
                "app.services.agent_identity_service.create_channel_event_message"
            ) as create_event,
        ):
            now = datetime.now(UTC)

            def build_membership(_db, membership):
                membership.id = 12
                membership.joined_at = now
                membership.created_at = now
                membership.updated_at = now
                return membership

            create_membership.side_effect = build_membership

            result = service.add_agent_to_channel(
                self.db,
                self.user,
                self.server.id,
                self.channel.id,
                ChannelAgentMemberCreateRequest(agent_identity_id=agent_identity.id),
            )

        require_admin.assert_called_once_with(self.db, self.server.id, self.user.id)
        create_membership.assert_called_once()
        create_event.assert_called_once()
        self.assertEqual(
            create_event.call_args.kwargs["event_type"], "channel.agent_joined"
        )
        self.assertEqual(
            create_event.call_args.kwargs["target"].target_agent_identity_id,
            agent_identity.id,
        )
        self.assertEqual(result.channel_id, self.channel.id)
        self.assertEqual(result.agent_identity_id, agent_identity.id)
        self.db.commit.assert_called_once()

    def test_add_agent_to_channel_requires_server_admin(self) -> None:
        service = AgentIdentityService(persistent_runtime_service=MagicMock())
        agent_identity_id = uuid.uuid4()

        with (
            patch(
                "app.services.agent_identity_service.require_server_admin",
                side_effect=Exception("forbidden"),
            ) as require_admin,
            patch(
                "app.services.agent_identity_service.ServerChannelRepository.get_by_id"
            ) as get_channel,
            patch(
                "app.services.agent_identity_service.ServerChannelAgentMemberRepository.create"
            ) as create_membership,
        ):
            with self.assertRaisesRegex(Exception, "forbidden"):
                service.add_agent_to_channel(
                    self.db,
                    self.user,
                    self.server.id,
                    self.channel.id,
                    ChannelAgentMemberCreateRequest(
                        agent_identity_id=agent_identity_id
                    ),
                )

        require_admin.assert_called_once_with(self.db, self.server.id, self.user.id)
        get_channel.assert_not_called()
        create_membership.assert_not_called()

    def test_restart_agent_cancels_current_execution_without_canceling_queue(
        self,
    ) -> None:
        persistent_runtime_service = MagicMock()
        persistent_runtime_service.ensure_server_agent_runtime.return_value = (
            SimpleNamespace(runtime_key="server_agent:test")
        )
        persistent_runtime_service.get_runtime.return_value = None
        service = AgentIdentityService(
            persistent_runtime_service=persistent_runtime_service
        )
        session_id = uuid.uuid4()
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        agent_identity.persistent_state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=agent_identity.id,
            state_root_path="agents/state",
            profile_path="agents/state/profile.json",
            memory_path="agents/state/MEMORY.md",
            notes_dir_path="agents/state/notes",
            state_dir_path="agents/state/state",
            artifacts_dir_path="agents/state/artifacts",
            state_version=1,
            runtime_status="busy",
            active_session_id=session_id,
            active_task_id=uuid.uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        persistent_runtime_service._sync_legacy_owner_state.side_effect = (
            lambda _db, _runtime, channel_task_id: (
                setattr(agent_identity.persistent_state, "runtime_status", "idle"),
                setattr(agent_identity.persistent_state, "active_session_id", None),
                setattr(agent_identity.persistent_state, "active_task_id", None),
            )
        )

        with (
            patch(
                "app.services.agent_identity_service.require_server_owner",
                return_value=MagicMock(role="owner"),
            ) as require_owner,
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_id",
                return_value=agent_identity,
            ),
            patch(
                "app.services.agent_identity_service.SessionService.cancel_current_execution"
            ) as cancel_current_execution,
        ):
            result = service.restart_agent(
                self.db,
                self.user,
                self.server.id,
                agent_identity.id,
            )

        require_owner.assert_called_once_with(self.db, self.server.id, self.user.id)
        cancel_current_execution.assert_called_once_with(
            self.db,
            session_id,
            user_id=agent_identity.created_by,
            reason="Agent restarted",
        )
        persistent_state = agent_identity.persistent_state
        assert persistent_state is not None
        self.assertEqual(persistent_state.runtime_status, "idle")
        self.assertIsNone(persistent_state.active_session_id)
        self.assertIsNone(persistent_state.active_task_id)
        self.assertEqual(result.agent_identity_id, agent_identity.id)
        self.db.commit.assert_called_once()

    def test_remove_agent_from_server_soft_removes_identity_and_memberships(
        self,
    ) -> None:
        persistent_runtime_service = MagicMock()
        persistent_runtime_service.ensure_server_agent_runtime.return_value = (
            SimpleNamespace(runtime_key="server_agent:test")
        )
        service = AgentIdentityService(
            persistent_runtime_service=persistent_runtime_service
        )
        session_id = uuid.uuid4()
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        agent_identity.persistent_state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=agent_identity.id,
            state_root_path="agents/state",
            profile_path="agents/state/profile.json",
            memory_path="agents/state/MEMORY.md",
            notes_dir_path="agents/state/notes",
            state_dir_path="agents/state/state",
            artifacts_dir_path="agents/state/artifacts",
            state_version=1,
            runtime_status="busy",
            active_session_id=session_id,
            active_task_id=uuid.uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        membership = ServerChannelAgentMember(
            id=1,
            channel_id=self.channel.id,
            agent_identity_id=agent_identity.id,
            role="member",
            joined_at=datetime.now(UTC),
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.agent_identity_service.require_server_owner",
                return_value=MagicMock(role="owner"),
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.get_by_id",
                return_value=agent_identity,
            ),
            patch(
                "app.services.agent_identity_service.SessionService.cancel_session"
            ) as cancel_session,
            patch(
                "app.services.agent_identity_service.SessionQueueItemRepository.list_active_by_agent_scope",
                return_value=[],
            ),
            patch(
                "app.services.agent_identity_service.ServerChannelMessageRepository.list_open_execution_placeholders_by_agent_scope",
                return_value=[],
            ),
            patch(
                "app.services.agent_identity_service.ServerChannelAgentMemberRepository.list_by_agent",
                return_value=[membership],
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.delete"
            ) as delete_agent,
        ):
            service.remove_agent_from_server(
                self.db,
                self.user,
                self.server.id,
                agent_identity.id,
            )

        cancel_session.assert_called_once_with(
            self.db,
            session_id,
            user_id=agent_identity.created_by,
            reason="Agent removed from server",
        )
        delete_agent.assert_not_called()
        self.assertEqual(agent_identity.lifecycle_state, "inactive")
        self.assertIsNotNone(agent_identity.removed_at)
        self.assertEqual(agent_identity.removed_by, self.user.id)
        self.assertEqual(membership.status, "removed")
        self.db.commit.assert_called_once()

    def test_list_agents_does_not_create_runtime_rows_on_read(self) -> None:
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        agent_identity.persistent_state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=agent_identity.id,
            state_root_path="agents/state",
            profile_path="agents/state/profile.json",
            memory_path="agents/state/MEMORY.md",
            notes_dir_path="agents/state/notes",
            state_dir_path="agents/state/state",
            artifacts_dir_path="agents/state/artifacts",
            state_version=1,
            runtime_status="idle",
            active_session_id=None,
            active_task_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        persistent_runtime_service = MagicMock()
        persistent_runtime_service.build_server_agent_runtime_summary.return_value = (
            None
        )
        service = AgentIdentityService(
            persistent_runtime_service=persistent_runtime_service
        )

        with (
            patch(
                "app.services.agent_identity_service.require_server_member",
                return_value=MagicMock(role="member"),
            ),
            patch(
                "app.services.agent_identity_service.AgentIdentityRepository.list_by_server",
                return_value=[agent_identity],
            ),
        ):
            result = service.list_agents(self.db, self.user, self.server.id)

        self.assertEqual(len(result), 1)
        persistent_runtime_service.ensure_server_agent_runtime.assert_not_called()
        persistent_runtime_service.build_server_agent_runtime_summary.assert_called_once()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
