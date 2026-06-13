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
from app.schemas.agent_trigger import TriggerReferences
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest, TaskEnqueueResponse
from app.services.channel_shared_context_service import ChannelSharedContextService
from app.services.persistent_runtime_service import PersistentRuntimeService
from app.services.task_service import TaskService


class ServerAgentTriggerService:
    MENTION_PATTERN = re.compile(r"(?:^|\s)@([^\s@,.!?;:]+)(?=$|[\s,.!?;:])")

    def __init__(
        self,
        *,
        task_service: TaskService | None = None,
        shared_context_service: ChannelSharedContextService | None = None,
        persistent_runtime_service: PersistentRuntimeService | None = None,
    ) -> None:
        self._task_service = task_service or TaskService()
        self._shared_context_service = (
            shared_context_service or ChannelSharedContextService()
        )
        self._persistent_runtime_service = (
            persistent_runtime_service or PersistentRuntimeService()
        )

    def _effective_thread_root_message_id(self, message) -> uuid.UUID | None:
        thread_root_message_id = getattr(message, "thread_root_message_id", None)
        if thread_root_message_id is not None:
            return thread_root_message_id

        content = getattr(message, "content", None)
        if isinstance(content, dict) and content.get("as_task") is True:
            return getattr(message, "id", None)
        return None

    @staticmethod
    def _message_entities(message) -> list[dict] | None:
        content = getattr(message, "content", None)
        if not isinstance(content, dict) or "entities" not in content:
            return None
        entities = content.get("entities")
        if isinstance(entities, list):
            return [item for item in entities if isinstance(item, dict)]
        return []

    @staticmethod
    def _entity_target_uuid(entity: dict) -> uuid.UUID | None:
        target_id = entity.get("target_id") or entity.get("targetId")
        if target_id is None:
            return None
        try:
            return uuid.UUID(str(target_id))
        except ValueError:
            return None

    @staticmethod
    def _append_unique(values: list[uuid.UUID], value: uuid.UUID | None) -> None:
        if value is not None and value not in values:
            values.append(value)

    def _collect_trigger_references(self, message) -> TriggerReferences:
        message_id = getattr(message, "id")
        message_ids: list[uuid.UUID] = [message_id]
        artifact_ids: list[uuid.UUID] = []
        task_ids: list[uuid.UUID] = []
        entities = self._message_entities(message) or []

        for entity in entities:
            target_id = self._entity_target_uuid(entity)
            kind = entity.get("kind")
            action = entity.get("action")
            if action != "reference":
                continue
            if kind == "artifact":
                self._append_unique(artifact_ids, target_id)
            elif kind == "task":
                self._append_unique(task_ids, target_id)
            elif kind in {"message", "thread"}:
                self._append_unique(message_ids, target_id)

        return TriggerReferences(
            message_ids=message_ids,
            artifact_ids=artifact_ids,
            task_ids=task_ids,
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
        thread_root_message_id = self._effective_thread_root_message_id(message)
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

        entities = self._message_entities(message)
        if entities is not None:
            matched = []
            seen_agent_ids: set[uuid.UUID] = set()
            for entity in entities:
                if entity.get("kind") != "agent" or entity.get("action") != "trigger":
                    continue
                agent_identity_id = self._entity_target_uuid(entity)
                if agent_identity_id is None or agent_identity_id in seen_agent_ids:
                    continue
                membership = (
                    ServerChannelAgentMemberRepository.get_by_channel_and_agent(
                        db,
                        channel.id,
                        agent_identity_id,
                    )
                )
                agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
                if (
                    membership is None
                    or membership.status != "active"
                    or agent is None
                    or agent.lifecycle_state != "active"
                    or agent.removed_at is not None
                ):
                    continue
                seen_agent_ids.add(agent_identity_id)
                matched.append(agent)
            # Structured agent-trigger entities are authoritative when present: they
            # let us ignore stray @handle regex matches the sender did not intend. But
            # if the entities carry no resolvable agent (e.g. only file references), we
            # must fall through to the @handle text fallback so plain-mention replies
            # still trigger instead of being silently dropped.
            if matched:
                return matched

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
        thread_root_message_id = self._effective_thread_root_message_id(
            message
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
                references=self._collect_trigger_references(message),
            )
            runtime = self._persistent_runtime_service.ensure_server_agent_runtime(
                db,
                agent_identity=agent,
            )
            active_session_id = runtime.session_id

            request = TaskEnqueueRequest(
                prompt=trigger_body,
                session_id=active_session_id,
                permission_mode="acceptEdits",
                schedule_mode="immediate",
                client_request_id=f"channel-trigger:{message.id}:{agent.id}",
                config=TaskConfig(
                    preset_id=agent.preset_id,
                    container_mode="persistent",
                    persistent_runtime_key=runtime.runtime_key,
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
