import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel_message import ServerChannelMessage
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.schemas.agent_trigger import (
    AgentTriggerEnvelope,
    TriggerHandoff,
    TriggerReferences,
    TriggerSourceActor,
)
from app.schemas.channel_runtime import (
    AgentChannelAgentResponse,
    AgentChannelAgentsListResponse,
    AgentChannelCollaborationRequest,
    AgentChannelCollaborationResponse,
    AgentChannelMessageReadRequest,
    AgentChannelMessagesReadResponse,
    AgentChannelRuntimeScope,
)
from app.schemas.session import TaskConfig
from app.schemas.task import TaskEnqueueRequest
from app.services.channel_runtime_scope_service import ChannelRuntimeScopeService
from app.services.persistent_runtime_service import PersistentRuntimeService
from app.services.server_channel_message_reaction_service import (
    ServerChannelMessageReactionService,
)
from app.services.server_channel_message_service import ServerChannelMessageService
from app.services.task_service import TaskService


class ChannelRuntimeService:
    MAX_COLLABORATION_DEPTH = 2

    def __init__(
        self,
        *,
        scope_service: ChannelRuntimeScopeService | None = None,
        task_service: TaskService | None = None,
        persistent_runtime_service: PersistentRuntimeService | None = None,
    ) -> None:
        self._scope_service = scope_service or ChannelRuntimeScopeService()
        self._task_service = task_service or TaskService()
        self._persistent_runtime_service = (
            persistent_runtime_service or PersistentRuntimeService()
        )

    def read_messages(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelMessageReadRequest,
    ) -> AgentChannelMessagesReadResponse:
        scope = self._scope_service.resolve_scope(db, session_id=session_id)
        has_selector = bool(
            request.message_ids
            or request.thread_root_message_id is not None
            or request.anchor_message_id is not None
        )
        limit = self._normalize_limit(request.limit)
        timeline_limit = None if request.read_all and not has_selector else limit
        messages: list[ServerChannelMessage] = []

        for message_id in request.message_ids[:limit]:
            messages.append(
                self._require_message_in_scope(
                    db,
                    scope=scope,
                    message_id=message_id,
                )
            )

        if request.thread_root_message_id is not None:
            root = self._require_message_in_scope(
                db,
                scope=scope,
                message_id=request.thread_root_message_id,
            )
            root_id = root.thread_root_message_id or root.id
            if root.thread_root_message_id is not None:
                root = self._require_message_in_scope(
                    db,
                    scope=scope,
                    message_id=root_id,
                )
            messages.append(root)
            messages.extend(
                ServerChannelMessageRepository.list_replies(
                    db,
                    root_id,
                    limit=max(0, limit - 1),
                )
            )

        if request.anchor_message_id is not None and len(messages) < limit:
            anchor = self._require_message_in_scope(
                db,
                scope=scope,
                message_id=request.anchor_message_id,
            )
            remaining = limit - len(messages)
            if request.include_anchor and remaining > 0:
                messages.append(anchor)
                remaining -= 1
            if remaining > 0:
                messages.extend(
                    ServerChannelMessageRepository.list_from_anchor(
                        db,
                        scope.channel_id,
                        anchor_message=anchor,
                        direction=request.direction or "before",
                        limit=remaining,
                    )
                )

        if not has_selector:
            if request.read_all:
                messages.extend(
                    ServerChannelMessageRepository.list_all_by_channel(
                        db,
                        scope.channel_id,
                        limit=timeline_limit,
                    )
                )
            else:
                messages.extend(
                    ServerChannelMessageRepository.list_by_channel(
                        db,
                        scope.channel_id,
                        before_message_id=None,
                        limit=timeline_limit,
                    )
                )

        messages = self._dedupe_messages(messages)
        if timeline_limit is not None:
            messages = messages[:timeline_limit]
        for message in messages:
            if message.channel_id != scope.channel_id:
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Message not found: {message.id}",
                )

        reply_counts = ServerChannelMessageRepository.count_replies_by_roots(
            db,
            [message.id for message in messages],
        )
        reactions = ServerChannelMessageReactionService().list_grouped_by_messages(
            db,
            [message.id for message in messages],
            current_agent_identity_id=scope.agent_identity_id,
        )

        return AgentChannelMessagesReadResponse(
            messages=[
                ServerChannelMessageService._build_message_response(
                    message,
                    reply_count=reply_counts.get(message.id, 0),
                    reactions=reactions.get(message.id, []),
                )
                for message in messages
            ]
        )

    def list_agents(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> AgentChannelAgentsListResponse:
        scope = self._scope_service.resolve_scope(db, session_id=session_id)
        agents: list[AgentChannelAgentResponse] = []
        for membership in ServerChannelAgentMemberRepository.list_by_channel(
            db,
            scope.channel_id,
        ):
            if membership.status != "active":
                continue
            agent = AgentIdentityRepository.get_by_id(
                db,
                membership.agent_identity_id,
            )
            if (
                agent is None
                or agent.server_id != scope.server_id
                or agent.lifecycle_state != "active"
            ):
                continue
            agents.append(
                AgentChannelAgentResponse(
                    agent_identity_id=agent.id,
                    handle=agent.handle,
                    display_name=agent.display_name,
                    description=agent.description,
                    visual_key=agent.visual_key,
                )
            )
        return AgentChannelAgentsListResponse(agents=agents)

    def request_collaboration(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelCollaborationRequest,
    ) -> AgentChannelCollaborationResponse:
        scope = self._scope_service.resolve_scope(db, session_id=session_id)
        target_handle = request.agent_handle.strip()
        if not target_handle:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="agent_handle must not be empty",
            )
        if target_handle.lower() == scope.agent_handle.lower():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Collaboration cannot target the current agent",
            )
        if scope.handoff_depth >= self.MAX_COLLABORATION_DEPTH:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Collaboration hop depth exceeded",
            )

        target_agent = AgentIdentityRepository.get_by_server_and_handle(
            db,
            scope.server_id,
            target_handle,
        )
        if (
            target_agent is None
            or target_agent.lifecycle_state != "active"
            or target_agent.server_id != scope.server_id
        ):
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent not found in channel: {target_handle}",
            )
        if target_agent.id == scope.agent_identity_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Collaboration cannot target the current agent",
            )

        membership = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel_id=scope.channel_id,
            agent_identity_id=target_agent.id,
        )
        if membership is None or membership.status != "active":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Target agent is not an active member of this channel",
            )

        trigger_message_id = scope.trigger_message_id or scope.thread_root_message_id
        if trigger_message_id is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing collaboration trigger message context",
            )
        thread_root_message_id = (
            request.thread_root_message_id
            or scope.thread_root_message_id
            or trigger_message_id
        )
        dedupe_key = (
            f"agent-collaboration:{scope.session_id}:{target_agent.id}:"
            f"{trigger_message_id}:{request.mode}"
        )
        trigger_context = AgentTriggerEnvelope(
            trigger_type="agent_collaboration",
            server_id=scope.server_id,
            channel_id=scope.channel_id,
            trigger_message_id=trigger_message_id,
            thread_root_message_id=thread_root_message_id,
            target_agent_identity_id=target_agent.id,
            target_agent_handle=target_agent.handle,
            source_actor=TriggerSourceActor(
                actor_type="agent",
                agent_identity_id=scope.agent_identity_id,
                display_name=scope.agent_label,
            ),
            references=TriggerReferences(
                message_ids=request.reference_message_ids or [trigger_message_id],
                artifact_ids=request.reference_artifact_ids,
            ),
            handoff=TriggerHandoff(
                parent_run_id=getattr(scope, "parent_run_id", None),
                depth=scope.handoff_depth + 1,
                dedupe_key=dedupe_key,
            ),
        )
        runtime = self._persistent_runtime_service.ensure_server_agent_runtime(
            db,
            agent_identity=target_agent,
        )
        active_session_id = runtime.session_id
        result = self._task_service.enqueue_task(
            db,
            target_agent.created_by,
            TaskEnqueueRequest(
                prompt=request.request_text.strip(),
                session_id=active_session_id,
                permission_mode="acceptEdits",
                schedule_mode="immediate",
                client_request_id=dedupe_key,
                config=TaskConfig(
                    preset_id=target_agent.preset_id,
                    container_mode="persistent",
                    persistent_runtime_key=runtime.runtime_key,
                    filesystem_mode="sandbox",
                    agent_identity_id=target_agent.id,
                    agent_runtime_mode="persistent",
                    server_id=scope.server_id,
                    channel_id=scope.channel_id,
                    trigger_message_id=trigger_message_id,
                    thread_root_message_id=thread_root_message_id,
                    trigger_type="agent_collaboration",
                    trigger_context=trigger_context,
                ),
            ),
        )
        trigger_message = ServerChannelMessageRepository.get_by_id(
            db,
            trigger_message_id,
        )
        if trigger_message is not None:
            from app.services.server_agent_trigger_service import (
                ServerAgentTriggerService,
            )

            ServerAgentTriggerService()._create_execution_placeholder(
                db,
                channel_id=scope.channel_id,
                message=trigger_message,
                agent=target_agent,
                result=result,
            )
        return AgentChannelCollaborationResponse(
            status=result.status,
            target_agent_identity_id=target_agent.id,
            target_agent_handle=target_agent.handle,
            session_id=result.session_id,
            run_id=result.run_id,
            queue_item_id=result.queue_item_id,
            dedupe_key=dedupe_key,
        )

    @staticmethod
    def _normalize_limit(value: int | None) -> int:
        if value is None:
            return 50
        return max(1, min(int(value), 100))

    @staticmethod
    def _dedupe_messages(
        messages: list[ServerChannelMessage],
    ) -> list[ServerChannelMessage]:
        seen: set[uuid.UUID] = set()
        deduped: list[ServerChannelMessage] = []
        for message in messages:
            if message.id in seen:
                continue
            seen.add(message.id)
            deduped.append(message)
        return deduped

    @staticmethod
    def _require_message_in_scope(
        db: Session,
        *,
        scope: AgentChannelRuntimeScope,
        message_id: uuid.UUID,
    ) -> ServerChannelMessage:
        message = ServerChannelMessageRepository.get_by_id(db, message_id)
        if message is None or message.channel_id != scope.channel_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Message not found: {message_id}",
            )
        return message
