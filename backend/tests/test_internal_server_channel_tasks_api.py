import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_db, require_internal_token
from app.main import create_app
from app.schemas.server_channel_task import ServerChannelTaskResponse


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
        title="Review retry behavior",
        description="Agent created task",
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


class InternalServerChannelTasksApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.app.dependency_overrides[get_db] = lambda: object()
        self.app.dependency_overrides[require_internal_token] = lambda: None
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.internal_server_channel_tasks.service.create_task")
    def test_create_internal_server_channel_task_returns_payload(
        self, create_task
    ) -> None:
        task = build_task_response(server_id=self.server_id, channel_id=self.channel_id)
        create_task.return_value = {
            "action": "create_channel_task",
            "task": task.model_dump(mode="json"),
            "thread_root_message_id": str(task.thread_root_message_id),
        }

        response = self.client.post(
            f"/api/v1/internal/server-channel-tasks/create?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={"title": "Review retry behavior"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["action"], "create_channel_task")
        create_task.assert_called_once()

    @patch("app.api.v1.internal_server_channel_tasks.service.list_tasks")
    def test_list_internal_server_channel_tasks_returns_payload(
        self, list_tasks
    ) -> None:
        task = build_task_response(server_id=self.server_id, channel_id=self.channel_id)
        list_tasks.return_value = {
            "action": "list_channel_tasks",
            "tasks": [task.model_dump(mode="json")],
        }

        response = self.client.post(
            f"/api/v1/internal/server-channel-tasks/list?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={"status": "todo", "limit": 20},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["action"], "list_channel_tasks")
        list_tasks.assert_called_once()

    @patch("app.api.v1.internal_server_channel_tasks.service.read_task")
    def test_read_internal_server_channel_task_returns_payload(self, read_task) -> None:
        task = build_task_response(server_id=self.server_id, channel_id=self.channel_id)
        read_task.return_value = {
            "action": "read_channel_task",
            "task": task.model_dump(mode="json"),
            "thread_root_message_id": str(task.thread_root_message_id),
        }

        response = self.client.post(
            f"/api/v1/internal/server-channel-tasks/read?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={"task_id": str(task.task_id)},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["action"], "read_channel_task")
        read_task.assert_called_once()

    @patch("app.api.v1.internal_server_channel_tasks.service.comment_on_task")
    def test_comment_internal_server_channel_task_returns_payload(
        self, comment_on_task
    ) -> None:
        task = build_task_response(server_id=self.server_id, channel_id=self.channel_id)
        comment_on_task.return_value = {
            "action": "comment_on_channel_task",
            "task": task.model_dump(mode="json"),
            "thread_root_message_id": str(task.thread_root_message_id),
        }

        response = self.client.post(
            f"/api/v1/internal/server-channel-tasks/comment?session_id={self.session_id}",
            headers={"X-Internal-Token": "change-this-token-in-production"},
            json={
                "task_id": str(task.task_id),
                "text": "I have started the investigation.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["action"], "comment_on_channel_task")
        comment_on_task.assert_called_once()


if __name__ == "__main__":
    unittest.main()
