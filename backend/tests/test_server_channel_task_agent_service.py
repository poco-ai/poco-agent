import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.schemas.server_channel_task import ServerChannelTaskResponse
from app.schemas.server_channel_task_agent import (
    AgentChannelTaskCommentRequest,
    AgentChannelTaskCreateRequest,
    AgentChannelTaskListRequest,
    AgentChannelTaskReadRequest,
)
from app.services.server_channel_task_agent_service import (
    ServerChannelTaskAgentService,
)


class ServerChannelTaskAgentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.service = ServerChannelTaskAgentService()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.thread_root_message_id = uuid.uuid4()

    def test_resolve_context_reads_channel_scope_from_session_snapshot(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="user-1",
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
                "thread_root_message_id": str(self.thread_root_message_id),
            },
        )
        agent = SimpleNamespace(
            id=self.agent_identity_id,
            server_id=self.server_id,
            handle="backend-specialist",
            display_name="Backend Specialist",
            preset_id=7,
        )

        with (
            patch(
                "app.services.server_channel_task_agent_service.SessionRepository.get_by_id",
                return_value=session,
            ),
            patch(
                "app.services.server_channel_task_agent_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
        ):
            context = self.service.resolve_context(self.db, session_id=self.session_id)

        self.assertEqual(context.session_id, self.session_id)
        self.assertEqual(context.server_id, self.server_id)
        self.assertEqual(context.channel_id, self.channel_id)
        self.assertEqual(context.agent_identity_id, self.agent_identity_id)
        self.assertEqual(context.thread_root_message_id, self.thread_root_message_id)
        self.assertEqual(context.agent_handle, "backend-specialist")
        self.assertEqual(context.agent_preset_id, 7)

    def test_resolve_context_rejects_missing_channel_scope(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="user-1",
            config_snapshot={
                "server_id": str(self.server_id),
                "agent_identity_id": str(self.agent_identity_id),
            },
        )

        with patch(
            "app.services.server_channel_task_agent_service.SessionRepository.get_by_id",
            return_value=session,
        ):
            with self.assertRaises(AppException) as context:
                self.service.resolve_context(self.db, session_id=self.session_id)

        self.assertIn("channel task context", str(context.exception))

    def test_create_task_uses_resolved_context_and_service_boundary(self) -> None:
        context = SimpleNamespace(
            session_id=self.session_id,
            user_id="user-1",
            server_id=self.server_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            agent_handle="backend-specialist",
            agent_label="Backend Specialist",
            agent_preset_id=7,
            thread_root_message_id=self.thread_root_message_id,
        )
        task = ServerChannelTaskResponse(
            task_id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel_id,
            display_number=1,
            title="Review retry design",
            description="Need a tracked item",
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
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
        )

        with (
            patch.object(self.service, "resolve_context", return_value=context),
            patch.object(
                self.service._task_service, "create_task", return_value=task
            ) as create_task,
        ):
            result = self.service.create_task(
                self.db,
                session_id=self.session_id,
                request=AgentChannelTaskCreateRequest(
                    title="Review retry design",
                    description="Need a tracked item",
                ),
            )

        create_task.assert_called_once()
        self.assertEqual(result.action, "create_channel_task")
        self.assertEqual(result.task.task_id, task.task_id)
        self.assertEqual(result.thread_root_message_id, task.thread_root_message_id)

    def test_list_tasks_reads_current_channel_tasks(self) -> None:
        context = SimpleNamespace(
            session_id=self.session_id,
            user_id="user-1",
            server_id=self.server_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            agent_handle="backend-specialist",
            agent_label="Backend Specialist",
            agent_preset_id=7,
            thread_root_message_id=self.thread_root_message_id,
        )
        task = ServerChannelTaskResponse(
            task_id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel_id,
            display_number=1,
            title="Review retry design",
            description=None,
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
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
        )

        with (
            patch.object(self.service, "resolve_context", return_value=context),
            patch.object(
                self.service._task_service,
                "list_tasks",
                return_value=[task],
            ) as list_tasks,
        ):
            result = self.service.list_tasks(
                self.db,
                session_id=self.session_id,
                request=AgentChannelTaskListRequest(status="todo", limit=10),
            )

        list_tasks.assert_called_once()
        self.assertEqual(result.action, "list_channel_tasks")
        self.assertEqual([item.task_id for item in result.tasks], [task.task_id])

    def test_read_task_uses_current_channel_scope(self) -> None:
        context = SimpleNamespace(
            session_id=self.session_id,
            user_id="user-1",
            server_id=self.server_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            agent_handle="backend-specialist",
            agent_label="Backend Specialist",
            agent_preset_id=7,
            thread_root_message_id=self.thread_root_message_id,
        )
        task = ServerChannelTaskResponse(
            task_id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel_id,
            display_number=1,
            title="Review retry design",
            description=None,
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
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
        )

        with (
            patch.object(self.service, "resolve_context", return_value=context),
            patch.object(
                self.service._task_service,
                "get_task",
                return_value=task,
            ) as get_task,
        ):
            result = self.service.read_task(
                self.db,
                session_id=self.session_id,
                request=AgentChannelTaskReadRequest(task_id=task.task_id),
            )

        get_task.assert_called_once()
        self.assertEqual(result.action, "read_channel_task")
        self.assertEqual(result.task.task_id, task.task_id)

    def test_comment_on_task_uses_service_boundary(self) -> None:
        context = SimpleNamespace(
            session_id=self.session_id,
            user_id="user-1",
            server_id=self.server_id,
            channel_id=self.channel_id,
            agent_identity_id=self.agent_identity_id,
            agent_handle="backend-specialist",
            agent_label="Backend Specialist",
            agent_preset_id=7,
            thread_root_message_id=self.thread_root_message_id,
        )
        task = ServerChannelTaskResponse(
            task_id=uuid.uuid4(),
            server_id=self.server_id,
            channel_id=self.channel_id,
            display_number=1,
            title="Review retry design",
            description=None,
            status="in_progress",
            position=0,
            priority="medium",
            due_date=None,
            assignee_user_id=None,
            assignee_preset_id=7,
            reporter_user_id=None,
            related_project_id=None,
            creator_user_id="user-1",
            updated_by="user-1",
            thread_root_message_id=uuid.uuid4(),
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
        )

        with (
            patch.object(self.service, "resolve_context", return_value=context),
            patch.object(
                self.service._task_service,
                "comment_on_task",
                return_value=task,
            ) as comment_on_task,
        ):
            result = self.service.comment_on_task(
                self.db,
                session_id=self.session_id,
                request=AgentChannelTaskCommentRequest(
                    task_id=task.task_id,
                    text="I have started the investigation.",
                ),
            )

        comment_on_task.assert_called_once()
        self.assertEqual(result.action, "comment_on_channel_task")
        self.assertEqual(result.task.task_id, task.task_id)


if __name__ == "__main__":
    unittest.main()
