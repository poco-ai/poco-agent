import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.server_channel import ServerChannel
from app.models.server_channel_task import ServerChannelTask
from app.models.user import User
from app.schemas.server_channel_task import (
    ServerChannelTaskClaimRequest,
    ServerChannelTaskCreateRequest,
    ServerChannelTaskStatusUpdateRequest,
)
from app.services.server_channel_task_service import ServerChannelTaskService


class ServerChannelTaskServiceTests(unittest.TestCase):
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
            name="backend",
            slug="backend",
            visibility="public",
            created_by="user-1",
            archived_at=None,
        )

    def test_create_task_creates_task_and_root_message(self) -> None:
        service = ServerChannelTaskService()

        with (
            patch.object(service, "_require_channel_access", return_value=self.channel),
            patch(
                "app.services.server_channel_task_service.ServerChannelTaskRepository.list_by_channel_and_status",
                return_value=[],
            ),
            patch(
                "app.services.server_channel_task_service.ServerChannelTaskRepository.create"
            ) as create_task,
            patch(
                "app.services.server_channel_task_service.ServerChannelTaskRepository.get_max_display_number",
                return_value=None,
            ),
            patch.object(service, "_create_task_root_message") as create_root_message,
        ):
            now = datetime.now(UTC)

            def build_task(_db, task):
                task.id = uuid.uuid4()
                task.created_at = now
                task.updated_at = now
                return task

            create_task.side_effect = build_task
            create_root_message.return_value = MagicMock(id=uuid.uuid4())

            result = service.create_task(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                ServerChannelTaskCreateRequest(
                    title="Refactor channel task detail",
                    description="Unify task activity blocks",
                    status="todo",
                ),
            )

        create_task.assert_called_once()
        create_root_message.assert_called_once()
        created_task = create_task.call_args.args[1]
        self.assertEqual(created_task.title, "Refactor channel task detail")
        self.assertEqual(result.channel_id, self.channel.id)
        self.db.commit.assert_called_once()

    def test_create_task_root_message_is_event_without_author(self) -> None:
        service = ServerChannelTaskService()
        task = ServerChannelTask(
            id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel.id,
            display_number=1,
            title="Ship board view",
            description=None,
            status="todo",
            position=0,
            priority="medium",
            creator_user_id="user-1",
            updated_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(service, "_create_message") as create_message:
            service._create_task_root_message(
                self.db,
                current_user=self.user,
                task=task,
            )

        create_message.assert_called_once()
        kwargs = create_message.call_args.kwargs
        self.assertIsNone(kwargs["author_user_id"])
        self.assertEqual(kwargs["message_type"], "event")
        self.assertEqual(kwargs["content"]["event_type"], "task.created")
        self.assertEqual(kwargs["content"]["actor_type"], "user")

    def test_create_task_root_message_records_source_message_without_replying(
        self,
    ) -> None:
        service = ServerChannelTaskService()
        source_message_id = uuid.uuid4()
        task = ServerChannelTask(
            id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel.id,
            display_number=1,
            title="Ship board view",
            description=None,
            status="todo",
            position=0,
            priority="medium",
            creator_user_id="user-1",
            updated_by="user-1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(service, "_create_message") as create_message:
            service._create_task_root_message(
                self.db,
                current_user=self.user,
                task=task,
                source_message_id=source_message_id,
            )

        create_message.assert_called_once()
        kwargs = create_message.call_args.kwargs
        self.assertEqual(kwargs["message_type"], "event")
        self.assertIsNone(kwargs.get("thread_root_message_id"))
        self.assertEqual(
            kwargs["content"]["source_message_id"],
            str(source_message_id),
        )

    def test_update_task_status_emits_event_message_for_status_change(self) -> None:
        service = ServerChannelTaskService()
        task = ServerChannelTask(
            id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel.id,
            display_number=1,
            title="Ship board view",
            description=None,
            status="todo",
            position=0,
            priority="medium",
            creator_user_id="user-1",
            updated_by="user-1",
            thread_root_message_id=uuid.uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch.object(
                service,
                "_require_task_access",
                return_value=(self.channel, task),
            ),
            patch.object(service, "_move_task_within_channel") as move_task,
            patch.object(service, "_create_system_message") as create_system_message,
        ):

            def apply_move(_db, moved_task, *, target_status, target_position):
                moved_task.status = target_status
                moved_task.position = target_position

            move_task.side_effect = apply_move

            result = service.update_task_status(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                task.id,
                ServerChannelTaskStatusUpdateRequest(
                    status="in_review",
                    position=0,
                ),
            )

        create_system_message.assert_called_once()
        self.assertEqual(create_system_message.call_args.kwargs["event"], "task.status_changed")
        self.assertEqual(result.status, "in_review")
        self.db.commit.assert_called_once()

    def test_task_status_system_message_helper_creates_event_reply(self) -> None:
        service = ServerChannelTaskService()
        root_id = uuid.uuid4()
        task = ServerChannelTask(
            id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel.id,
            display_number=1,
            title="Ship board view",
            description=None,
            status="in_review",
            position=0,
            priority="medium",
            creator_user_id="user-1",
            updated_by="user-1",
            thread_root_message_id=root_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(service, "_create_message") as create_message:
            service._create_system_message(
                self.db,
                current_user=self.user,
                task=task,
                event="task.status_changed",
                text_preview="Alice moved task to in review",
                extra_content={"from_status": "todo", "to_status": "in_review"},
            )

        create_message.assert_called_once()
        kwargs = create_message.call_args.kwargs
        self.assertIsNone(kwargs["author_user_id"])
        self.assertEqual(kwargs["message_type"], "event")
        self.assertEqual(kwargs["thread_root_message_id"], root_id)
        self.assertEqual(kwargs["content"]["event_type"], "task.status_changed")

    def test_claim_task_defaults_to_current_user(self) -> None:
        service = ServerChannelTaskService()
        task = ServerChannelTask(
            id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel.id,
            display_number=1,
            title="Review detail drawer",
            description=None,
            status="todo",
            position=0,
            priority="medium",
            creator_user_id="user-1",
            updated_by="user-1",
            thread_root_message_id=uuid.uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch.object(
                service,
                "_require_task_access",
                return_value=(self.channel, task),
            ),
            patch.object(service, "_create_system_message") as create_system_message,
        ):
            result = service.claim_task(
                self.db,
                self.user,
                self.server_id,
                self.channel.id,
                task.id,
                ServerChannelTaskClaimRequest(),
            )

        create_system_message.assert_called_once()
        self.assertEqual(create_system_message.call_args.kwargs["event"], "task.assigned")
        self.assertEqual(task.assignee_user_id, "user-1")
        self.assertEqual(result.assignee_user_id, "user-1")


if __name__ == "__main__":
    unittest.main()
