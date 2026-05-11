import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.server_channel_message import ServerChannelMessage
from app.schemas.agent_trigger import AgentTriggerEnvelope, TriggerSourceActor
from app.models.user import User
from app.schemas.callback import AgentCallbackRequest, CallbackStatus
from app.schemas.task import TaskEnqueueResponse
from app.services.callback_service import CallbackService
from app.services.server_agent_trigger_service import ServerAgentTriggerService


class ServerExecutionObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_id = uuid.uuid4()
        self.session_id = uuid.uuid4()
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )

    def test_trigger_creates_execution_placeholder_after_enqueue(self) -> None:
        task_service = MagicMock()
        context_service = MagicMock()
        service = ServerAgentTriggerService(
            task_service=task_service,
            shared_context_service=context_service,
        )
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist",
            content={"text": "Please review @api-specialist"},
            thread_root_message_id=None,
        )
        channel = SimpleNamespace(
            id=self.channel_id,
            server_id=self.server_id,
            conversation_type="channel",
            direct_agent_identity_id=None,
            name="backend",
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            server_id=self.server_id,
            preset_id=8,
            handle="api-specialist",
            display_name="API Specialist",
            visual_key="preset-visual-01",
            lifecycle_state="active",
            created_by="owner-user",
            removed_at=None,
            persistent_state=SimpleNamespace(active_session_id=None),
        )
        membership = SimpleNamespace(
            agent_identity_id=self.agent_id,
            status="active",
        )
        context_service.extract_trigger_body.return_value = "shared prompt"
        context_service.build_trigger_envelope.return_value = AgentTriggerEnvelope(
            trigger_type="channel_mention",
            server_id=self.server_id,
            channel_id=self.channel_id,
            trigger_message_id=message.id,
            thread_root_message_id=message.id,
            target_agent_identity_id=self.agent_id,
            target_agent_handle="api-specialist",
            source_actor=TriggerSourceActor(
                actor_type="user",
                user_id="user-1",
                display_name="Alice",
            ),
        )
        task_service.enqueue_task.return_value = TaskEnqueueResponse(
            session_id=self.session_id,
            accepted_type="run",
            run_id=uuid.uuid4(),
            status="queued",
            queued_query_count=0,
        )

        with (
            patch(
                "app.services.server_agent_trigger_service.ServerChannelAgentMemberRepository.list_by_channel",
                return_value=[membership],
            ),
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.server_agent_trigger_service.ServerChannelMessageRepository.create"
            ) as create_message,
        ):
            service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        placeholder = create_message.call_args.args[1]
        self.assertEqual(placeholder.message_type, "system")
        self.assertEqual(placeholder.channel_id, self.channel_id)
        self.assertEqual(placeholder.content["source"], "agent_execution")
        self.assertEqual(placeholder.content["session_id"], str(self.session_id))
        self.assertEqual(placeholder.content["agent_handle"], "api-specialist")
        self.assertEqual(placeholder.content["trigger_message_id"], str(message.id))
        self.assertEqual(placeholder.thread_root_message_id, None)

    def test_as_task_trigger_creates_threaded_execution_placeholder(self) -> None:
        task_service = MagicMock()
        context_service = MagicMock()
        service = ServerAgentTriggerService(
            task_service=task_service,
            shared_context_service=context_service,
        )
        message = SimpleNamespace(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id="user-1",
            text_preview="Please review @api-specialist",
            content={"text": "Please review @api-specialist", "as_task": True},
            thread_root_message_id=None,
        )
        channel = SimpleNamespace(
            id=self.channel_id,
            server_id=self.server_id,
            conversation_type="channel",
            direct_agent_identity_id=None,
            name="backend",
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            server_id=self.server_id,
            preset_id=8,
            handle="api-specialist",
            display_name="API Specialist",
            visual_key="preset-visual-01",
            lifecycle_state="active",
            created_by="owner-user",
            removed_at=None,
            persistent_state=SimpleNamespace(active_session_id=None),
        )
        membership = SimpleNamespace(
            agent_identity_id=self.agent_id,
            status="active",
        )
        context_service.extract_trigger_body.return_value = "shared prompt"
        context_service.build_trigger_envelope.return_value = AgentTriggerEnvelope(
            trigger_type="channel_mention",
            server_id=self.server_id,
            channel_id=self.channel_id,
            trigger_message_id=message.id,
            thread_root_message_id=message.id,
            target_agent_identity_id=self.agent_id,
            target_agent_handle="api-specialist",
            source_actor=TriggerSourceActor(
                actor_type="user",
                user_id="user-1",
                display_name="Alice",
            ),
        )
        task_service.enqueue_task.return_value = TaskEnqueueResponse(
            session_id=self.session_id,
            accepted_type="run",
            run_id=uuid.uuid4(),
            status="queued",
            queued_query_count=0,
        )

        with (
            patch(
                "app.services.server_agent_trigger_service.ServerChannelAgentMemberRepository.list_by_channel",
                return_value=[membership],
            ),
            patch(
                "app.services.server_agent_trigger_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.server_agent_trigger_service.ServerChannelMessageRepository.create"
            ) as create_message,
        ):
            service.trigger_for_channel_message(
                self.db,
                current_user=self.current_user,
                server_id=self.server_id,
                channel=channel,
                message=message,
            )

        placeholder = create_message.call_args.args[1]
        self.assertEqual(placeholder.content["trigger_message_id"], str(message.id))
        self.assertEqual(
            placeholder.content["thread_root_message_id"], str(message.id)
        )
        self.assertEqual(placeholder.thread_root_message_id, message.id)

    def test_callback_updates_execution_placeholder_summary(self) -> None:
        service = CallbackService.__new__(CallbackService)
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "queued",
                "summary": None,
                "current_step": None,
                "todo_progress": {"completed": 0, "total": 0},
            },
            text_preview="queued",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(uuid.uuid4()),
            },
            state_patch=None,
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.RUNNING,
            progress=33,
            state_patch={
                "current_step": "Inspecting retry behavior",
                "todos": [
                    {"content": "inspect", "status": "completed"},
                    {"content": "patch", "status": "in_progress"},
                ],
            },
            new_message={
                "_type": "AssistantMessage",
                "content": [
                    {"_type": "TextBlock", "text": "Working on the retry path."}
                ],
            },
        )

        with patch(
            "app.services.callback_service.ServerChannelMessageRepository.find_execution_placeholder",
            return_value=placeholder,
        ):
            service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                callback=callback,
            )

        self.assertEqual(placeholder.content["execution_status"], "running")
        self.assertEqual(
            placeholder.content["current_step"], "Inspecting retry behavior"
        )
        self.assertEqual(placeholder.content["summary"], "Working on the retry path.")
        self.assertEqual(
            placeholder.content["todo_progress"],
            {"completed": 1, "total": 2},
        )

    def test_completed_callback_replaces_placeholder_with_final_agent_message(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        thread_root_message_id = uuid.uuid4()
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "running",
                "summary": "working",
                "actor_label": "API Specialist",
                "agent_label": "API Specialist",
                "agent_handle": "api-specialist",
                "agent_visual_key": "preset-visual-01",
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(thread_root_message_id),
                "todo_progress": {"completed": 0, "total": 0},
            },
            text_preview="working",
            thread_root_message_id=thread_root_message_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(thread_root_message_id),
            },
            state_patch=None,
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
            new_message={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Final answer"}],
            },
        )

        with patch(
            "app.services.callback_service.ServerChannelMessageRepository.find_execution_placeholder",
            return_value=placeholder,
        ):
            replaced = service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                callback=callback,
            )

        self.assertTrue(replaced)
        self.assertEqual(placeholder.content["source"], "agent_session")
        self.assertEqual(placeholder.content["text"], "Final answer")
        self.assertEqual(placeholder.content["actor_label"], "API Specialist")
        self.assertEqual(placeholder.thread_root_message_id, thread_root_message_id)

    def test_completed_callback_can_replace_already_completed_placeholder(self) -> None:
        service = CallbackService.__new__(CallbackService)
        thread_root_message_id = uuid.uuid4()
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "completed",
                "summary": "old summary",
                "actor_label": "API Specialist",
                "agent_label": "API Specialist",
                "agent_handle": "api-specialist",
                "agent_visual_key": "preset-visual-01",
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(thread_root_message_id),
                "todo_progress": {"completed": 0, "total": 0},
            },
            text_preview="old summary",
            thread_root_message_id=thread_root_message_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(thread_root_message_id),
            },
            state_patch=None,
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
            new_message={
                "_type": "AssistantMessage",
                "content": [
                    {"_type": "TextBlock", "text": "Final answer after replay"}
                ],
            },
        )

        with patch(
            "app.services.callback_service.ServerChannelMessageRepository.find_execution_placeholder",
            return_value=placeholder,
        ):
            replaced = service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                callback=callback,
            )

        self.assertTrue(replaced)
        self.assertEqual(placeholder.content["source"], "agent_session")
        self.assertEqual(placeholder.content["text"], "Final answer after replay")

    def test_mirror_assistant_message_reuses_existing_placeholder(self) -> None:
        service = CallbackService.__new__(CallbackService)
        thread_root_message_id = uuid.uuid4()
        trigger_message_id = uuid.uuid4()
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "completed",
                "summary": "summary",
                "agent_handle": "api-specialist",
                "agent_visual_key": "preset-visual-01",
                "trigger_message_id": str(trigger_message_id),
            },
            text_preview="summary",
            thread_root_message_id=thread_root_message_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
                "trigger_message_id": str(trigger_message_id),
                "thread_root_message_id": str(thread_root_message_id),
            },
        )
        db_message = SimpleNamespace(
            id=123,
            role="assistant",
            text_preview="Final answer preview",
            content={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Final answer full"}],
            },
        )
        agent = SimpleNamespace(
            id=self.agent_id,
            display_name="API Specialist",
            handle="api-specialist",
            visual_key="preset-visual-01",
        )

        with (
            patch(
                "app.services.callback_service.ServerChannelMessageRepository.find_session_projection_by_run",
                return_value=placeholder,
            ),
            patch(
                "app.services.callback_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.callback_service.ServerChannelMessageRepository.create"
            ) as create_message,
        ):
            service._mirror_assistant_message_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                db_message=db_message,
            )

        create_message.assert_not_called()
        self.assertEqual(placeholder.content["source"], "agent_session")
        self.assertEqual(placeholder.content["text"], "Final answer full")
        self.assertEqual(placeholder.text_preview, "Final answer full")

    def test_completed_callback_preserves_existing_full_agent_session_text(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        long_text = "Final answer " * 80
        summary = long_text[:280]
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_session",
                "session_id": str(self.session_id),
                "execution_status": "running",
                "summary": summary,
                "text": long_text,
                "actor_label": "API Specialist",
                "agent_handle": "api-specialist",
                "agent_visual_key": "preset-visual-01",
            },
            text_preview=long_text,
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
            },
            state_patch=None,
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
        )

        with patch(
            "app.services.callback_service.ServerChannelMessageRepository.find_execution_placeholder",
            return_value=placeholder,
        ):
            replaced = service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                callback=callback,
            )

        self.assertTrue(replaced)
        self.assertEqual(placeholder.content["source"], "agent_session")
        self.assertEqual(placeholder.content["text"], long_text.strip())
        self.assertEqual(placeholder.text_preview, long_text.strip())

    def test_completed_callback_does_not_promote_summary_to_final_text(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        summary = "Summary " * 40
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "running",
                "summary": summary,
                "actor_label": "API Specialist",
            },
            text_preview=summary,
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
            },
            state_patch=None,
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
        )

        with patch(
            "app.services.callback_service.ServerChannelMessageRepository.find_execution_placeholder",
            return_value=placeholder,
        ):
            replaced = service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                callback=callback,
            )

        self.assertFalse(replaced)
        self.assertEqual(placeholder.content["source"], "agent_execution")
        self.assertEqual(placeholder.content["execution_status"], "completed")
        self.assertNotIn("text", placeholder.content)
        self.assertEqual(placeholder.text_preview, summary.strip())

    def test_latest_channel_projectable_assistant_prefers_non_result_message(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        final_message = SimpleNamespace(
            id=10,
            role="assistant",
            text_preview="Full assistant answer",
            content={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Full assistant answer"}],
            },
        )
        result_message = SimpleNamespace(
            id=11,
            role="assistant",
            text_preview="Summary only",
            content={"_type": "ResultMessage", "result": "Summary only"},
        )
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = [result_message, final_message]
        self.db.query.return_value = query

        selected = service._latest_channel_projectable_assistant_message(
            self.db,
            self.session_id,
        )

        self.assertIs(selected, final_message)

    def test_completed_teardown_callback_uses_prior_assistant_message_without_new_message(
        self,
    ) -> None:
        service = CallbackService()
        db_session = SimpleNamespace(
            id=self.session_id,
            status="running",
            sdk_session_id=None,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
            },
            workspace_export_status=None,
            workspace_files_prefix=None,
            workspace_manifest_key=None,
            workspace_archive_key=None,
        )
        prior_message = SimpleNamespace(
            id=12,
            role="assistant",
            text_preview="Final assistant answer",
            content={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Final assistant answer"}],
            },
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
        )
        service._im_events = MagicMock()
        service._assignment_service = MagicMock()
        service._channel_artifact_service = MagicMock()
        service._im_events.enqueue_assistant_message_created.side_effect = RuntimeError(
            "should not enqueue assistant-message event without a raw message"
        )

        with (
            patch.object(
                service,
                "_resolve_session_and_run",
                return_value=(db_session, None),
            ),
            patch.object(
                service,
                "_sync_execution_placeholder_to_server_channel",
                return_value=False,
            ),
            patch.object(
                service,
                "_latest_channel_projectable_assistant_message",
                return_value=prior_message,
            ),
            patch.object(
                service,
                "_mirror_assistant_message_to_server_channel",
            ) as mirror_message,
            patch.object(service, "_should_apply_workspace_export", return_value=True),
            patch.object(
                service,
                "_should_preserve_existing_ready_workspace",
                return_value=False,
            ),
            patch.object(service, "_sync_agent_runtime"),
            patch(
                "app.services.callback_service.RunRepository.get_unfinished_by_session",
                return_value=None,
            ),
            patch(
                "app.services.callback_service.RunRepository.get_blocking_by_session",
                return_value=None,
            ),
            patch(
                "app.services.callback_service.session_queue_service.has_active_items",
                return_value=False,
            ),
            patch(
                "app.services.callback_service.pending_skill_creation_service.detect_and_create_pending"
            ),
        ):
            response = service.process_agent_callback(self.db, callback)

        self.assertEqual(response.status, "completed")
        self.assertEqual(db_session.status, "completed")
        mirror_message.assert_called_once_with(
            self.db,
            db_session=db_session,
            db_run=None,
            db_message=prior_message,
        )
        service._im_events.enqueue_assistant_message_created.assert_not_called()
        service._im_events.enqueue_run_terminal.assert_called_once()
        self.db.commit.assert_called_once()

    def test_mirror_prior_assistant_preserves_channel_root_projection_and_is_idempotent(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        trigger_message_id = uuid.uuid4()
        placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "channel_projection_message_id": "",
                "execution_status": "completed",
                "summary": "Execution completed.",
                "trigger_message_id": str(trigger_message_id),
                "thread_root_message_id": str(trigger_message_id),
            },
            text_preview="Execution completed.",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        placeholder.content["channel_projection_message_id"] = str(placeholder.id)
        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "channel_projection_message_id": str(placeholder.id),
                "agent_identity_id": str(self.agent_id),
                "trigger_message_id": str(trigger_message_id),
                "thread_root_message_id": str(trigger_message_id),
            },
        )
        db_message = SimpleNamespace(
            id=23,
            role="assistant",
            text_preview="Final channel answer",
            content={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Final channel answer"}],
            },
        )
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [placeholder]
        self.db.query.return_value = query

        with patch(
            "app.services.callback_service.AgentIdentityRepository.get_by_id",
            return_value=SimpleNamespace(
                id=self.agent_id,
                display_name="API Specialist",
                handle="api-specialist",
                visual_key="preset-visual-01",
            ),
        ):
            service._mirror_assistant_message_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                db_message=db_message,
            )
            service._mirror_assistant_message_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=None,
                db_message=db_message,
            )

        self.assertIsNone(placeholder.thread_root_message_id)
        self.assertEqual(placeholder.content["source"], "agent_session")
        self.assertEqual(placeholder.content["text"], "Final channel answer")
        self.db.add.assert_not_called()

    def test_find_execution_placeholder_prefers_run_id_over_session_only(self) -> None:
        run_id_target = uuid.uuid4()
        trigger_message_id = uuid.uuid4()
        thread_root_message_id = uuid.uuid4()
        newer_wrong = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "run_id": str(uuid.uuid4()),
                "trigger_message_id": str(uuid.uuid4()),
                "thread_root_message_id": str(uuid.uuid4()),
            },
            text_preview="wrong",
            thread_root_message_id=thread_root_message_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        correct = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "run_id": str(run_id_target),
                "trigger_message_id": str(trigger_message_id),
                "thread_root_message_id": str(thread_root_message_id),
            },
            text_preview="correct",
            thread_root_message_id=thread_root_message_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [newer_wrong, correct]
        self.db.query.return_value = query

        from app.repositories.server_channel_message_repository import (
            ServerChannelMessageRepository,
        )

        found = ServerChannelMessageRepository.find_execution_placeholder(
            self.db,
            channel_id=self.channel_id,
            session_id=self.session_id,
            run_id=run_id_target,
            trigger_message_id=trigger_message_id,
            thread_root_message_id=thread_root_message_id,
        )

        self.assertIs(found, correct)

    def test_find_execution_placeholder_does_not_fallback_when_identity_misses(
        self,
    ) -> None:
        queued_placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "queued",
                "summary": "@coworker is preparing a response.",
            },
            text_preview="@coworker is preparing a response.",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [queued_placeholder]
        self.db.query.return_value = query

        from app.repositories.server_channel_message_repository import (
            ServerChannelMessageRepository,
        )

        found = ServerChannelMessageRepository.find_execution_placeholder(
            self.db,
            channel_id=self.channel_id,
            session_id=self.session_id,
            run_id=uuid.uuid4(),
            trigger_message_id=uuid.uuid4(),
        )

        self.assertIsNone(found)
        self.assertEqual(queued_placeholder.content["source"], "agent_execution")

    def test_callback_replaces_promoted_queue_placeholder_by_queue_item_id(
        self,
    ) -> None:
        service = CallbackService.__new__(CallbackService)
        queue_item_id = uuid.uuid4()
        run_id = uuid.uuid4()
        wrong_placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "execution_status": "queued",
                "summary": "Wrong queued placeholder",
            },
            text_preview="Wrong queued placeholder",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        correct_placeholder = ServerChannelMessage(
            id=uuid.uuid4(),
            channel_id=self.channel_id,
            author_user_id=None,
            message_type="system",
            content={
                "source": "agent_execution",
                "session_id": str(self.session_id),
                "queue_item_id": str(queue_item_id),
                "execution_status": "queued",
                "summary": "Queued placeholder",
            },
            text_preview="Queued placeholder",
            thread_root_message_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [wrong_placeholder, correct_placeholder]
        self.db.query.return_value = query

        db_session = SimpleNamespace(
            id=self.session_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
            },
        )
        db_run = SimpleNamespace(
            id=run_id,
            config_snapshot={
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_id),
                "queue_item_id": str(queue_item_id),
            },
        )
        callback = AgentCallbackRequest(
            session_id=str(self.session_id),
            run_id=str(run_id),
            time=datetime.now(UTC),
            status=CallbackStatus.COMPLETED,
            progress=100,
            new_message={
                "_type": "AssistantMessage",
                "content": [{"_type": "TextBlock", "text": "Second final answer"}],
            },
        )

        with patch(
            "app.services.callback_service.AgentIdentityRepository.get_by_id",
            return_value=SimpleNamespace(
                display_name="Jimi",
                handle="jimi",
                visual_key="preset-visual-02",
            ),
        ):
            replaced = service._sync_execution_placeholder_to_server_channel(
                self.db,
                db_session=db_session,
                db_run=db_run,
                callback=callback,
            )

        self.assertTrue(replaced)
        self.assertEqual(wrong_placeholder.content["source"], "agent_execution")
        self.assertEqual(wrong_placeholder.text_preview, "Wrong queued placeholder")
        self.assertEqual(correct_placeholder.content["source"], "agent_session")
        self.assertEqual(correct_placeholder.content["text"], "Second final answer")
        self.assertEqual(correct_placeholder.content["run_id"], str(run_id))
        self.assertEqual(
            correct_placeholder.content["queue_item_id"], str(queue_item_id)
        )


if __name__ == "__main__":
    unittest.main()
