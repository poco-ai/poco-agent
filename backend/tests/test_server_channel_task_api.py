import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.server_channel_task import (
    ServerChannelTaskCandidateResponse,
    ServerChannelTaskResponse,
)


def build_task_response(
    *,
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
) -> ServerChannelTaskResponse:
    now = datetime.now(UTC)
    return ServerChannelTaskResponse(
        task_id=uuid.uuid4(),
        server_id=server_id,
        channel_id=channel_id,
        display_number=1,
        title="Refine channel activity",
        description="Keep task updates inside the channel thread",
        status="todo",
        position=0,
        priority="medium",
        due_date=None,
        assignee_user_id=None,
        assignee_preset_id=None,
        reporter_user_id=None,
        related_project_id=None,
        creator_user_id="user-1",
        updated_by="user-1",
        thread_root_message_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


class ServerChannelTaskApiTests(unittest.TestCase):
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

    @patch("app.api.v1.server_channel_tasks.service.create_task")
    def test_create_server_channel_task_returns_payload(self, create_task) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        task = build_task_response(server_id=server_id, channel_id=channel_id)
        create_task.return_value = task

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/tasks",
            json={"title": "Refine channel activity"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["task_id"], str(task.task_id))
        create_task.assert_called_once()

    @patch("app.api.v1.server_channel_tasks.service.list_tasks")
    def test_list_server_channel_tasks_returns_collection(self, list_tasks) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        task = build_task_response(server_id=server_id, channel_id=channel_id)
        list_tasks.return_value = [task]

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/tasks",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["task_id"], str(task.task_id))
        list_tasks.assert_called_once()

    @patch("app.api.v1.server_channel_tasks.service.list_task_candidates")
    def test_list_server_channel_task_candidates_returns_collection(
        self,
        list_task_candidates,
    ) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        task_id = uuid.uuid4()
        list_task_candidates.return_value = [
            ServerChannelTaskCandidateResponse(
                task_id=task_id,
                display_number=42,
                title="Review structured mentions",
                status="todo",
            )
        ]

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/tasks/candidates",
            params={"q": "mentions", "limit": 10},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["task_id"], str(task_id))
        self.assertEqual(body["data"][0]["display_number"], 42)
        list_task_candidates.assert_called_once()

    @patch("app.api.v1.server_channel_tasks.service.claim_task")
    def test_claim_server_channel_task_returns_task_payload(self, claim_task) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        task = build_task_response(server_id=server_id, channel_id=channel_id)
        claim_task.return_value = task

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/tasks/{task.task_id}/claim",
            json={},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["task_id"], str(task.task_id))
        claim_task.assert_called_once()


if __name__ == "__main__":
    unittest.main()
