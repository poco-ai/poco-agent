import unittest
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors.exceptions import AppException
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invite import WorkspaceInvite
from app.schemas.workspace_invite import (
    WorkspaceInviteAcceptRequest,
    WorkspaceInviteCreateRequest,
    WorkspaceInviteRevokeRequest,
)
from app.schemas.workspace_member import WorkspaceMemberRoleUpdateRequest
from app.schemas.workspace_tenancy import (
    WorkspaceCreateRequest,
    WorkspaceOwnershipTransferRequest,
)
from app.services.workspace_invite_service import WorkspaceInviteService
from app.services.workspace_member_service import WorkspaceMemberService
from app.services.workspace_service import WorkspaceService


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def _build_workspace(
        self,
        *,
        name: str,
        slug: str,
        kind: str,
        owner_user_id: str = "user-1",
    ) -> Workspace:
        now = datetime.now(UTC)
        return Workspace(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            kind=kind,
            owner_user_id=owner_user_id,
            created_at=now,
            updated_at=now,
        )

    def test_list_workspaces_creates_personal_workspace_when_missing(self) -> None:
        personal_workspace = self._build_workspace(
            name="Alice's Workspace",
            slug="personal-user-1",
            kind="personal",
        )
        service = WorkspaceService()

        with (
            patch(
                "app.services.workspace_service.WorkspaceRepository.get_personal_by_owner",
                return_value=None,
            ) as get_personal_by_owner,
            patch(
                "app.services.workspace_service.WorkspaceRepository.get_by_slug",
                return_value=None,
            ) as get_by_slug,
            patch(
                "app.services.workspace_service.WorkspaceRepository.create"
            ) as create_workspace,
            patch(
                "app.services.workspace_service.WorkspaceMemberRepository.create"
            ) as create_member,
            patch(
                "app.services.workspace_service.WorkspaceRepository.list_by_user",
                return_value=[personal_workspace],
            ) as list_by_user,
        ):
            create_workspace.side_effect = lambda _db, workspace: workspace

            result = service.list_workspaces(self.db, self.user)

        get_personal_by_owner.assert_called_once_with(self.db, "user-1")
        get_by_slug.assert_called_once_with(self.db, "personal-user-1")
        create_workspace.assert_called_once()
        create_member.assert_called_once()
        list_by_user.assert_called_once_with(self.db, "user-1")
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].kind, "personal")
        self.assertEqual(result[0].slug, "personal-user-1")

    def test_create_workspace_creates_owner_membership(self) -> None:
        shared_workspace = self._build_workspace(
            name="Poco Core Team",
            slug="poco-core-team",
            kind="shared",
        )
        service = WorkspaceService()

        with (
            patch.object(service, "ensure_personal_workspace") as ensure_personal,
            patch(
                "app.services.workspace_service.WorkspaceRepository.get_by_slug",
                return_value=None,
            ) as get_by_slug,
            patch(
                "app.services.workspace_service.WorkspaceRepository.create"
            ) as create_workspace,
            patch(
                "app.services.workspace_service.WorkspaceMemberRepository.create"
            ) as create_member,
        ):
            create_workspace.side_effect = lambda _db, workspace: shared_workspace

            result = service.create_workspace(
                self.db,
                self.user,
                WorkspaceCreateRequest(name="Poco Core Team"),
            )

        ensure_personal.assert_called_once_with(self.db, self.user)
        get_by_slug.assert_called_once_with(self.db, "poco-core-team")
        create_workspace.assert_called_once()
        create_member.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(shared_workspace)
        self.assertEqual(result.kind, "shared")
        self.assertEqual(result.slug, "poco-core-team")

    def test_owner_can_transfer_shared_workspace_ownership(self) -> None:
        shared_workspace = self._build_workspace(
            name="Poco Core Team",
            slug="poco-core-team",
            kind="shared",
        )
        current_owner = MagicMock(
            workspace_id=shared_workspace.id,
            user_id="user-1",
            role="owner",
            status="active",
        )
        next_owner = MagicMock(
            workspace_id=shared_workspace.id,
            user_id="user-2",
            role="member",
            status="active",
        )
        service = WorkspaceService()

        with (
            patch(
                "app.services.workspace_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                side_effect=[current_owner, next_owner, current_owner],
            ),
            patch(
                "app.services.workspace_service.WorkspaceRepository.get_by_id",
                return_value=shared_workspace,
            ),
        ):
            result = service.transfer_ownership(
                self.db,
                self.user,
                shared_workspace.id,
                WorkspaceOwnershipTransferRequest(new_owner_user_id="user-2"),
            )

        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(shared_workspace)
        self.assertEqual(shared_workspace.owner_user_id, "user-2")
        self.assertEqual(current_owner.role, "admin")
        self.assertEqual(next_owner.role, "owner")
        self.assertEqual(result.owner_user_id, "user-2")

    def test_owner_can_soft_delete_shared_workspace(self) -> None:
        shared_workspace = self._build_workspace(
            name="Poco Core Team",
            slug="poco-core-team",
            kind="shared",
        )
        owner_membership = MagicMock(role="owner", status="active")
        service = WorkspaceService()

        with (
            patch(
                "app.services.workspace_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=owner_membership,
            ),
            patch(
                "app.services.workspace_service.WorkspaceRepository.get_by_id",
                return_value=shared_workspace,
            ),
        ):
            service.delete_workspace(self.db, self.user, shared_workspace.id)

        self.db.commit.assert_called_once()
        self.assertTrue(shared_workspace.is_deleted)


class WorkspaceMemberServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.workspace_id = uuid.uuid4()
        self.owner_membership = MagicMock(
            id=1,
            workspace_id=self.workspace_id,
            user_id="user-1",
            role="owner",
            joined_at=datetime.now(UTC),
            invited_by=None,
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.member_membership = MagicMock(
            id=2,
            workspace_id=self.workspace_id,
            user_id="user-2",
            role="member",
            joined_at=datetime.now(UTC),
            invited_by="user-1",
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_list_members_requires_existing_membership(self) -> None:
        service = WorkspaceMemberService()

        with patch(
            "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
            return_value=None,
        ):
            with self.assertRaises(AppException):
                service.list_members(self.db, self.current_user, self.workspace_id)

    def test_update_member_role_requires_owner(self) -> None:
        service = WorkspaceMemberService()

        with (
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=self.member_membership,
            ),
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_id",
                return_value=self.member_membership,
            ),
        ):
            with self.assertRaises(AppException):
                service.update_member_role(
                    self.db,
                    self.current_user,
                    self.workspace_id,
                    self.member_membership.id,
                    WorkspaceMemberRoleUpdateRequest(role="admin"),
                )

    def test_owner_can_update_member_role(self) -> None:
        service = WorkspaceMemberService()

        with (
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=self.owner_membership,
            ),
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_id",
                return_value=self.member_membership,
            ),
        ):
            result = service.update_member_role(
                self.db,
                self.current_user,
                self.workspace_id,
                self.member_membership.id,
                WorkspaceMemberRoleUpdateRequest(role="admin"),
            )

        self.db.commit.assert_called_once()
        self.assertEqual(self.member_membership.role, "admin")
        self.assertEqual(result.role, "admin")

    def test_owner_can_remove_non_owner_member(self) -> None:
        service = WorkspaceMemberService()

        with (
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=self.owner_membership,
            ),
            patch(
                "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_id",
                return_value=self.member_membership,
            ),
        ):
            service.remove_member(
                self.db,
                self.current_user,
                self.workspace_id,
                self.member_membership.id,
            )

        self.db.delete.assert_called_once_with(self.member_membership)
        self.db.commit.assert_called_once()

    def test_member_can_leave_workspace(self) -> None:
        service = WorkspaceMemberService()

        with patch(
            "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
            return_value=self.member_membership,
        ):
            service.leave_workspace(self.db, self.current_user, self.workspace_id)

        self.db.delete.assert_called_once_with(self.member_membership)
        self.db.commit.assert_called_once()


class WorkspaceInviteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.owner = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.member = User(
            id="user-2",
            primary_email="bob@example.com",
            display_name="Bob",
            avatar_url=None,
            status="active",
        )
        self.workspace = Workspace(
            id=uuid.uuid4(),
            name="Poco Core Team",
            slug="poco-core-team",
            kind="shared",
            owner_user_id="user-1",
        )

    def test_create_invite_requires_owner(self) -> None:
        service = WorkspaceInviteService()

        with patch(
            "app.services.workspace_invite_service.WorkspaceRepository.get_by_id",
            return_value=self.workspace,
        ):
            with self.assertRaises(AppException):
                service.create_invite(
                    self.db,
                    self.member,
                    self.workspace.id,
                    WorkspaceInviteCreateRequest(role="member", expires_in_days=7),
                )

    def test_admin_can_create_invite(self) -> None:
        service = WorkspaceInviteService()
        admin_membership = MagicMock(
            workspace_id=self.workspace.id,
            user_id="user-2",
            role="admin",
            status="active",
        )

        with (
            patch(
                "app.services.workspace_invite_service.WorkspaceRepository.get_by_id",
                return_value=self.workspace,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=admin_membership,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceInviteRepository.create"
            ) as create_invite,
        ):
            def build_invite(_db, invite):
                invite.id = uuid.uuid4()
                invite.created_at = datetime.now(UTC)
                invite.updated_at = datetime.now(UTC)
                return invite

            create_invite.side_effect = build_invite

            result = service.create_invite(
                self.db,
                self.member,
                self.workspace.id,
                WorkspaceInviteCreateRequest(role="member", expires_in_days=7),
            )

        self.db.commit.assert_called_once()
        create_invite.assert_called_once()
        self.assertEqual(result.role, "member")

    def test_accept_invite_creates_membership_and_consumes_usage(self) -> None:
        service = WorkspaceInviteService()
        invite = WorkspaceInvite(
            id=uuid.uuid4(),
            workspace_id=self.workspace.id,
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
                "app.services.workspace_invite_service.WorkspaceInviteRepository.get_by_token",
                return_value=invite,
            ) as get_by_token,
            patch(
                "app.services.workspace_invite_service.WorkspaceRepository.get_by_id",
                return_value=self.workspace,
            ) as get_workspace,
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=None,
            ) as get_membership,
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.create"
            ) as create_membership,
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
                self.member,
                WorkspaceInviteAcceptRequest(token="invite-token"),
            )

        get_by_token.assert_called_once_with(self.db, "invite-token")
        get_workspace.assert_called_once_with(self.db, self.workspace.id)
        get_membership.assert_called_once_with(self.db, self.workspace.id, "user-2")
        create_membership.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertEqual(invite.used_count, 1)
        self.assertEqual(result.workspace_id, self.workspace.id)
        self.assertEqual(result.user_id, "user-2")

    def test_accept_invite_emits_invite_accepted_and_member_joined_audit_events(
        self,
    ) -> None:
        db = sessionmaker(bind=create_engine("sqlite:///:memory:"))()
        service = WorkspaceInviteService()
        invite = WorkspaceInvite(
            id=uuid.uuid4(),
            workspace_id=self.workspace.id,
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
        membership = MagicMock(
            id=1,
            workspace_id=self.workspace.id,
            user_id="user-2",
            role="member",
            joined_at=datetime.now(UTC),
            invited_by="user-1",
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "app.services.workspace_invite_service.WorkspaceInviteRepository.get_by_token",
                return_value=invite,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceRepository.get_by_id",
                return_value=self.workspace,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=None,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.create",
                return_value=membership,
            ),
            patch(
                "app.services.activity_logger.ActivityLogger.log_activity",
                return_value=None,
            ) as log_activity,
        ):
            service.accept_invite(
                db,
                self.member,
                WorkspaceInviteAcceptRequest(token="invite-token"),
            )

        actions = [call.args[1].action for call in log_activity.call_args_list]
        self.assertCountEqual(
            actions,
            ["workspace.invite_accepted", "workspace.member_joined"],
        )

    def test_admin_can_revoke_invite(self) -> None:
        service = WorkspaceInviteService()
        invite = WorkspaceInvite(
            id=uuid.uuid4(),
            workspace_id=self.workspace.id,
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
        admin_membership = MagicMock(
            workspace_id=self.workspace.id,
            user_id="user-2",
            role="admin",
            status="active",
        )

        with (
            patch(
                "app.services.workspace_invite_service.WorkspaceInviteRepository.get_by_id",
                return_value=invite,
            ),
            patch(
                "app.services.workspace_invite_service.WorkspaceMemberRepository.get_by_workspace_and_user",
                return_value=admin_membership,
            ),
        ):
            result = service.revoke_invite(
                self.db,
                self.member,
                self.workspace.id,
                invite.id,
                WorkspaceInviteRevokeRequest(),
            )

        self.db.commit.assert_called_once()
        self.assertIsNotNone(invite.revoked_at)
        self.assertEqual(result.invite_id, invite.id)


if __name__ == "__main__":
    unittest.main()
