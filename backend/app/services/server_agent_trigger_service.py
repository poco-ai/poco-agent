import re
import uuid

from sqlalchemy.orm import Session

from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.run_repository import RunRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.session_queue_item_repository import SessionQueueItemRepository
from app.models.server_channel_message import ServerChannelMessage
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest, TaskEnqueueResponse
from app.services.channel_shared_context_service import ChannelSharedContextService
from app.services.task_service import TaskService


class ServerAgentTriggerService:
    MENTION_PATTERN = re.compile(r"(?:^|\s)@([^\s@,.!?;:]+)(?=$|[\s,.!?;:])")

    def __init__(
        self,
        *,
        task_service: TaskService | None = None,
        shared_context_service: ChannelSharedContextService | None = None,
    ) -> None:
        self._task_service = task_service or TaskService()
        self._shared_context_service = (
            shared_context_service or ChannelSharedContextService()
        )

    def _create_execution_placeholder(
        self,
        db: Session,
        *,
        channel_id: uuid.UUID,
        message,
        agent,
        result: TaskEnqueueResponse,
    ) -> None:
        execution_status = "queued"
        if result.status in {"running", "completed", "failed"}:
            execution_status = result.status
        elif result.accepted_type == "queued_query":
            execution_status = "queued"

        trigger_message_id = getattr(message, "id", None)
        thread_root_message_id = getattr(message, "thread_root_message_id", None)
        logical_thread_root_message_id = thread_root_message_id or getattr(
            message, "id", None
        )
        summary = (
            f"@{agent.handle} is preparing a response."
            if execution_status == "queued"
            else f"@{agent.handle} is working."
        )
        placeholder = ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel_id,
                author_user_id=None,
                message_type="system",
                text_preview=summary,
                content={
                    "source": "agent_execution",
                    "session_id": str(result.session_id),
                    "run_id": str(result.run_id) if result.run_id else None,
                    "queue_item_id": str(result.queue_item_id)
                    if result.queue_item_id
                    else None,
                    "agent_identity_id": str(agent.id),
                    "agent_handle": agent.handle,
                    "actor_label": agent.display_name,
                    "agent_label": agent.display_name,
                    "agent_visual_key": getattr(agent, "visual_key", None),
                    "trigger_message_id": str(trigger_message_id)
                    if trigger_message_id
                    else None,
                    "thread_root_message_id": str(logical_thread_root_message_id)
                    if logical_thread_root_message_id
                    else None,
                    "execution_status": execution_status,
                    "summary": summary,
                    "current_step": None,
                    "todo_progress": {"completed": 0, "total": 0},
                },
                thread_root_message_id=thread_root_message_id,
            ),
        )
        db.flush()
        content = dict(placeholder.content or {})
        content["channel_projection_message_id"] = str(placeholder.id)
        placeholder.content = content

        if result.run_id is not None:
            run = RunRepository.get_by_id(db, result.run_id)
            if run is not None:
                snapshot = (
                    dict(run.config_snapshot)
                    if isinstance(run.config_snapshot, dict)
                    else {}
                )
                snapshot["channel_projection_message_id"] = str(placeholder.id)
                run.config_snapshot = snapshot or None
        if result.queue_item_id is not None:
            item = SessionQueueItemRepository.get_by_id(db, result.queue_item_id)
            if item is not None:
                snapshot = (
                    dict(item.run_config_snapshot)
                    if isinstance(item.run_config_snapshot, dict)
                    else {}
                )
                snapshot["queue_item_id"] = str(item.id)
                snapshot["channel_projection_message_id"] = str(placeholder.id)
                item.run_config_snapshot = snapshot or None
        db.commit()

    def _collect_target_agents(
        self,
        db: Session,
        *,
        channel,
        message,
    ) -> list:
        if (
            channel.conversation_type == "direct_message"
            and channel.direct_agent_identity_id
        ):
            agent = AgentIdentityRepository.get_by_id(
                db, channel.direct_agent_identity_id
            )
            return [agent] if agent is not None else []

        message_text = ""
        content = getattr(message, "content", None)
        if isinstance(content, dict):
            raw_text = content.get("text")
            if isinstance(raw_text, str):
                message_text = raw_text
        if not message_text:
            message_text = getattr(message, "text_preview", "") or ""
        handles = {
            match.group(1).strip().lower()
            for match in self.MENTION_PATTERN.finditer(message_text)
            if match.group(1).strip()
        }
        if not handles:
            return []

        memberships = ServerChannelAgentMemberRepository.list_by_channel(db, channel.id)
        matched = []
        for membership in memberships:
            if membership.status != "active":
                continue
            agent = AgentIdentityRepository.get_by_id(db, membership.agent_identity_id)
            if (
                agent is None
                or agent.lifecycle_state != "active"
                or agent.removed_at is not None
            ):
                continue
            agent_handle = agent.handle.strip().lower()
            if agent_handle in handles:
                matched.append(agent)
        return matched

    def trigger_for_channel_message(
        self,
        db: Session,
        *,
        current_user,
        server_id: uuid.UUID,
        channel,
        message,
    ) -> list[TaskEnqueueResponse]:
        agents = self._collect_target_agents(
            db,
            channel=channel,
            message=message,
        )
        results: list[TaskEnqueueResponse] = []
        trigger_type = (
            "agent_dm"
            if channel.conversation_type == "direct_message"
            and channel.direct_agent_identity_id
            else "channel_mention"
        )
        thread_root_message_id = getattr(
            message, "thread_root_message_id", None
        ) or getattr(
            message,
            "id",
            None,
        )

        for agent in agents:
            trigger_body = self._shared_context_service.extract_trigger_body(message)
            trigger_context = self._shared_context_service.build_trigger_envelope(
                server_id=server_id,
                channel_id=channel.id,
                message=message,
                current_user=current_user,
                target_agent_identity_id=agent.id,
                target_agent_handle=agent.handle,
                trigger_type=trigger_type,
            )
            active_session_id = None
            if getattr(agent, "persistent_state", None) is not None:
                active_session_id = getattr(
                    agent.persistent_state,
                    "active_session_id",
                    None,
                )

            request = TaskEnqueueRequest(
                prompt=trigger_body,
                session_id=active_session_id,
                permission_mode="acceptEdits",
                schedule_mode="immediate",
                client_request_id=f"channel-trigger:{message.id}:{agent.id}",
                config=TaskConfig(
                    preset_id=agent.preset_id,
                    container_mode="persistent",
                    filesystem_mode="sandbox",
                    agent_identity_id=agent.id,
                    agent_runtime_mode="persistent",
                    server_id=server_id,
                    channel_id=channel.id,
                    trigger_message_id=message.id,
                    thread_root_message_id=thread_root_message_id,
                    trigger_type=trigger_type,
                    trigger_context=trigger_context,
                ),
            )
            results.append(
                self._task_service.enqueue_task(
                    db,
                    agent.created_by,
                    request,
                )
            )
            self._create_execution_placeholder(
                db,
                channel_id=channel.id,
                message=message,
                agent=agent,
                result=results[-1],
            )
        return results
