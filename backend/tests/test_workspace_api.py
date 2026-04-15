import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.activity_log import ActivityLogResponse
from app.schemas.workspace_invite import WorkspaceInviteResponse
from app.schemas.workspace_member import WorkspaceMemberResponse
from app.schemas.workspace_tenancy import WorkspaceResponse


def build_workspace_response() -> WorkspaceResponse:
    now = datetime.now(UTC)
    return WorkspaceResponse(
        workspace_id=uuid.uuid4(),
        name="Poco Core Team",
        slug="poco-core-team",
        kind="shared",
        owner_user_id="user-1",
        created_at=now,
        updated_at=now,
    )


def build_member_response(workspace_id: uuid.UUID) -> WorkspaceMemberResponse:
    now = datetime.now(UTC)
    return WorkspaceMemberResponse(
        membership_id=1,
        workspace_id=workspace_id,
        user_id="user-2",
        role="member",
        joined_at=now,
        invited_by="user-1",
        status="active",
        created_at=now,
        updated_at=now,
    )


def build_invite_response(workspace_id: uuid.UUID) -> WorkspaceInviteResponse:
    now = datetime.now(UTC)
    return WorkspaceInviteResponse(
        invite_id=uuid.uuid4(),
        workspace_id=workspace_id,
        token="invite-token",
        role="member",
        expires_at=now,
        created_by="user-1",
        max_uses=1,
        used_count=0,
        revoked_at=None,
        created_at=now,
        updated_at=now,
    )


def build_activity_response(workspace_id: uuid.UUID) -> ActivityLogResponse:
    return ActivityLogResponse(
        activity_log_id=uuid.uuid4(),
        workspace_id=workspace_id,
        actor_user_id="user-1",
        action="workspace.created",
        target_type="workspace",
        target_id=str(workspace_id),
        metadata={"name": "Poco Core Team"},
        created_at=datetime.now(UTC),
    )


class WorkspaceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.workspaces.service.list_workspaces")
    def test_list_workspaces_returns_response_envelope(self, list_workspaces) -> None:
        workspace = build_workspace_response()
        list_workspaces.return_value = [workspace]

        response = self.client.get("/api/v1/workspaces")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["workspace_id"], str(workspace.workspace_id))
        self.assertEqual(body["data"][0]["slug"], "poco-core-team")
        list_workspaces.assert_called_once()

    @patch("app.api.v1.workspace_invites.service.accept_invite")
    def test_accept_workspace_invite_returns_member_payload(self, accept_invite) -> None:
        workspace_id = uuid.uuid4()
        accept_invite.return_value = build_member_response(workspace_id)

        response = self.client.post(
            "/api/v1/workspace-invites/accept",
            json={"token": "invite-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["workspace_id"], str(workspace_id))
        self.assertEqual(body["data"]["user_id"], "user-2")
        accept_invite.assert_called_once()

    @patch("app.api.v1.workspace_invites.service.create_invite")
    def test_create_workspace_invite_returns_invite_payload(self, create_invite) -> None:
        workspace_id = uuid.uuid4()
        invite = build_invite_response(workspace_id)
        create_invite.return_value = invite

        response = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/invites",
            json={"role": "member", "expires_in_days": 7, "max_uses": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["token"], "invite-token")
        create_invite.assert_called_once()

    @patch("app.api.v1.workspace_members.service.update_member_role")
    def test_update_workspace_member_role_returns_member_payload(
        self,
        update_member_role,
    ) -> None:
        workspace_id = uuid.uuid4()
        update_member_role.return_value = build_member_response(workspace_id)

        response = self.client.patch(
            f"/api/v1/workspaces/{workspace_id}/members/1/role",
            json={"role": "admin"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["role"], "member")
        update_member_role.assert_called_once()

    @patch("app.api.v1.workspaces.service.transfer_ownership")
    def test_transfer_workspace_ownership_returns_workspace_payload(
        self,
        transfer_ownership,
    ) -> None:
        workspace = build_workspace_response()
        transfer_ownership.return_value = workspace

        response = self.client.post(
            f"/api/v1/workspaces/{workspace.workspace_id}/ownership-transfer",
            json={"new_owner_user_id": "user-2"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["workspace_id"], str(workspace.workspace_id))
        transfer_ownership.assert_called_once()

    @patch("app.api.v1.workspaces.service.delete_workspace")
    def test_delete_workspace_returns_workspace_id(self, delete_workspace) -> None:
        workspace_id = uuid.uuid4()

        response = self.client.delete(f"/api/v1/workspaces/{workspace_id}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["id"], str(workspace_id))
        delete_workspace.assert_called_once()

    @patch("app.api.v1.workspace_members.service.remove_member")
    def test_remove_workspace_member_returns_membership_id(self, remove_member) -> None:
        workspace_id = uuid.uuid4()

        response = self.client.delete(f"/api/v1/workspaces/{workspace_id}/members/1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["id"], 1)
        remove_member.assert_called_once()

    @patch("app.api.v1.workspace_members.service.leave_workspace")
    def test_leave_workspace_returns_workspace_id(self, leave_workspace) -> None:
        workspace_id = uuid.uuid4()

        response = self.client.post(f"/api/v1/workspaces/{workspace_id}/members/leave")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["workspace_id"], str(workspace_id))
        leave_workspace.assert_called_once()

    @patch("app.api.v1.activity_logs.require_workspace_member")
    @patch("app.api.v1.activity_logs.service.list_workspace_activity")
    def test_list_workspace_activity_returns_activity_payload(
        self,
        list_workspace_activity,
        require_workspace_member,
    ) -> None:
        workspace_id = uuid.uuid4()
        activity = build_activity_response(workspace_id)
        list_workspace_activity.return_value = [activity]

        response = self.client.get(f"/api/v1/workspaces/{workspace_id}/activity")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["action"], "workspace.created")
        self.assertEqual(body["data"][0]["metadata"]["name"], "Poco Core Team")
        require_workspace_member.assert_called_once()
        list_workspace_activity.assert_called_once()

    @patch("app.api.v1.workspace_invites.service.revoke_invite")
    def test_revoke_workspace_invite_returns_invite_payload(self, revoke_invite) -> None:
        workspace_id = uuid.uuid4()
        invite = build_invite_response(workspace_id)
        revoke_invite.return_value = invite

        response = self.client.post(
            f"/api/v1/workspaces/{workspace_id}/invites/{invite.invite_id}/revoke",
            json={},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["invite_id"], str(invite.invite_id))
        revoke_invite.assert_called_once()


if __name__ == "__main__":
    unittest.main()
