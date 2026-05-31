import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.agent_identity import AgentIdentityResponse


def build_agent_response(*, server_id: uuid.UUID) -> AgentIdentityResponse:
    now = datetime.now(UTC)
    return AgentIdentityResponse(
        agent_identity_id=uuid.uuid4(),
        server_id=server_id,
        preset_id=7,
        handle="backend-specialist",
        display_name="Backend Specialist",
        description="Owns backend architecture work",
        visual_key="preset-visual-02",
        visibility="server",
        lifecycle_state="active",
        created_by="user-1",
        updated_by="user-1",
        persistent_state=None,
        created_at=now,
        updated_at=now,
    )


class AgentIdentityApiTests(unittest.TestCase):
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

    @patch("app.api.v1.server_agents.service.create_agent")
    def test_create_server_agent_returns_agent_payload(self, create_agent) -> None:
        server_id = uuid.uuid4()
        agent = build_agent_response(server_id=server_id)
        create_agent.return_value = agent

        response = self.client.post(
            f"/api/v1/servers/{server_id}/agents",
            json={"display_name": "Backend Specialist", "preset_id": 7},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(
            body["data"]["agent_identity_id"], str(agent.agent_identity_id)
        )
        create_agent.assert_called_once()

    @patch("app.api.v1.server_agents.service.list_agents")
    def test_list_server_agents_returns_collection(self, list_agents) -> None:
        server_id = uuid.uuid4()
        agent = build_agent_response(server_id=server_id)
        list_agents.return_value = [agent]

        response = self.client.get(f"/api/v1/servers/{server_id}/agents")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["handle"], "backend-specialist")
        list_agents.assert_called_once()

    @patch("app.api.v1.server_agents.service.pin_agent_runtime")
    def test_pin_server_agent_runtime_returns_agent_payload(
        self,
        pin_agent_runtime,
    ) -> None:
        server_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        agent = build_agent_response(server_id=server_id)
        pin_agent_runtime.return_value = agent

        response = self.client.post(
            f"/api/v1/servers/{server_id}/agents/{agent_id}/pin",
            json={"duration_hours": 2},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(
            body["data"]["agent_identity_id"], str(agent.agent_identity_id)
        )
        pin_agent_runtime.assert_called_once()

    @patch("app.api.v1.server_agents.service.unpin_agent_runtime")
    def test_unpin_server_agent_runtime_returns_agent_payload(
        self,
        unpin_agent_runtime,
    ) -> None:
        server_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        agent = build_agent_response(server_id=server_id)
        unpin_agent_runtime.return_value = agent

        response = self.client.delete(
            f"/api/v1/servers/{server_id}/agents/{agent_id}/pin",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(
            body["data"]["agent_identity_id"], str(agent.agent_identity_id)
        )
        unpin_agent_runtime.assert_called_once()


if __name__ == "__main__":
    unittest.main()
