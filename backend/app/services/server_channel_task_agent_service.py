import uuid
from types import SimpleNamespace
from typing import cast

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.server_channel_task_agent import (
    AgentChannelTaskClaimSelfRequest,
    AgentChannelTaskCommentRequest,
    AgentChannelTaskContext,
    AgentChannelTaskCreateRequest,
    AgentChannelTaskListRequest,
    AgentChannelTaskListResponse,
    AgentChannelTaskOperationResponse,
    AgentChannelTaskReadRequest,
    AgentChannelTaskStatusRequest,
    to_claim_self_request,
    to_create_request,
    to_status_request,
)
from app.services.server_channel_task_service import (
    ServerChannelTaskService,
    TaskActorContext,
)


class ServerChannelTaskAgentService:
    def __init__(
        self,
        *,
        task_service: ServerChannelTaskService | None = None,
    ) -> None:
        self._task_service = task_service or ServerChannelTaskService()

    def resolve_context(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> AgentChannelTaskContext:
        session = SessionRepository.get_by_id(db, session_id)
        if session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        snapshot = session.config_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}

        try:
            server_id = uuid.UUID(str(snapshot.get("server_id")))
            channel_id = uuid.UUID(str(snapshot.get("channel_id")))
            agent_identity_id = uuid.UUID(str(snapshot.get("agent_identity_id")))
        except (TypeError, ValueError):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing channel task context",
            )

        thread_root_message_id = None
        raw_thread_root = snapshot.get("thread_root_message_id")
        if raw_thread_root is not None:
            try:
                thread_root_message_id = uuid.UUID(str(raw_thread_root))
            except (TypeError, ValueError):
                thread_root_message_id = None

        agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent is None or agent.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )

        return AgentChannelTaskContext(
            session_id=session.id,
            user_id=session.user_id,
            server_id=server_id,
            channel_id=channel_id,
            agent_identity_id=agent_identity_id,
            agent_handle=(agent.handle or "").strip() or str(agent.id),
            agent_label=(agent.display_name or "").strip()
            or (agent.handle or "").strip()
            or "Agent",
            agent_preset_id=agent.preset_id,
            thread_root_message_id=thread_root_message_id,
        )

    def _load_actor_user(self, context: AgentChannelTaskContext) -> User:
        return cast(
            User,
            SimpleNamespace(
                id=context.user_id,
                display_name=context.agent_label,
                primary_email=context.user_id,
            ),
        )

    def _build_actor_context(
        self,
        context: AgentChannelTaskContext,
    ) -> TaskActorContext:
        return TaskActorContext(
            actor_type="agent",
            actor_user_id=context.user_id,
            actor_label=context.agent_label,
            actor_agent_identity_id=context.agent_identity_id,
            actor_agent_handle=context.agent_handle,
            actor_session_id=context.session_id,
        )

    def create_task(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskCreateRequest,
    ) -> AgentChannelTaskOperationResponse:
        context = self.resolve_context(db, session_id=session_id)
        task = self._task_service.create_task(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
            to_create_request(request),
            actor_context=self._build_actor_context(context),
            source_thread_root_message_id=(
                request.thread_root_message_id or context.thread_root_message_id
            ),
        )
        return AgentChannelTaskOperationResponse(
            action="create_channel_task",
            task=task,
            thread_root_message_id=task.thread_root_message_id,
        )

    def list_tasks(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskListRequest,
    ) -> AgentChannelTaskListResponse:
        context = self.resolve_context(db, session_id=session_id)
        tasks = self._task_service.list_tasks(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
        )
        if request.status is not None:
            tasks = [task for task in tasks if task.status == request.status]
        if request.limit is not None:
            tasks = tasks[: request.limit]
        return AgentChannelTaskListResponse(tasks=tasks)

    def read_task(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskReadRequest,
    ) -> AgentChannelTaskOperationResponse:
        context = self.resolve_context(db, session_id=session_id)
        task = self._task_service.get_task(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
            request.task_id,
        )
        return AgentChannelTaskOperationResponse(
            action="read_channel_task",
            task=task,
            thread_root_message_id=task.thread_root_message_id,
        )

    def update_task_status(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskStatusRequest,
    ) -> AgentChannelTaskOperationResponse:
        context = self.resolve_context(db, session_id=session_id)
        task = self._task_service.update_task_status(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
            request.task_id,
            to_status_request(request),
            actor_context=self._build_actor_context(context),
        )
        return AgentChannelTaskOperationResponse(
            action="update_channel_task_status",
            task=task,
            thread_root_message_id=task.thread_root_message_id,
        )

    def claim_task(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskClaimSelfRequest,
    ) -> AgentChannelTaskOperationResponse:
        context = self.resolve_context(db, session_id=session_id)
        task = self._task_service.claim_task(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
            request.task_id,
            to_claim_self_request(
                assignee_agent_identity_id=context.agent_identity_id,
            ),
            actor_context=self._build_actor_context(context),
        )
        return AgentChannelTaskOperationResponse(
            action="claim_channel_task",
            task=task,
            thread_root_message_id=task.thread_root_message_id,
        )

    def comment_on_task(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        request: AgentChannelTaskCommentRequest,
    ) -> AgentChannelTaskOperationResponse:
        context = self.resolve_context(db, session_id=session_id)
        task = self._task_service.comment_on_task(
            db,
            self._load_actor_user(context),
            context.server_id,
            context.channel_id,
            request.task_id,
            request.text,
            actor_context=self._build_actor_context(context),
        )
        return AgentChannelTaskOperationResponse(
            action="comment_on_channel_task",
            task=task,
            thread_root_message_id=task.thread_root_message_id,
        )
