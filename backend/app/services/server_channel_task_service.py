import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agent_identity import AgentIdentity
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.server_channel_task import ServerChannelTask
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository
from app.repositories.server_channel_task_repository import (
    ServerChannelTaskRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.server_channel_task import (
    TASK_STATUS_VALUES,
    ChannelTaskActorSummary,
    ServerChannelTaskClaimRequest,
    ServerChannelTaskCreateRequest,
    ServerChannelTaskResponse,
    ServerChannelTaskStatusUpdateRequest,
    ServerChannelTaskUpdateRequest,
)
from app.services.server_member_service import require_server_member


@dataclass(slots=True)
class TaskActorContext:
    actor_type: str
    actor_user_id: str
    actor_label: str
    actor_agent_identity_id: uuid.UUID | None = None
    actor_agent_handle: str | None = None
    actor_session_id: uuid.UUID | None = None


class ServerChannelTaskService:
    def _build_task_response(
        self,
        db: Session,
        task: ServerChannelTask,
    ) -> ServerChannelTaskResponse:
        response = ServerChannelTaskResponse.model_validate(task)
        response.creator = self._user_summary(db, task.creator_user_id)
        response.assignee = self._assignee_summary(db, task)
        return response

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in TASK_STATUS_VALUES:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Unsupported channel task status: {status}",
            )

    @staticmethod
    def _normalize_position(position: int, max_position: int) -> int:
        return max(0, min(position, max_position))

    @staticmethod
    def _resequence_tasks(tasks: list[ServerChannelTask], status: str) -> None:
        for index, task in enumerate(tasks):
            task.status = status
            task.position = index

    @staticmethod
    def _assignee_payload(task: ServerChannelTask) -> dict[str, str | int] | None:
        if task.assignee_agent_identity_id is not None:
            return {
                "type": "agent",
                "agent_identity_id": str(task.assignee_agent_identity_id),
            }
        if task.assignee_preset_id is not None:
            return {"type": "agent", "preset_id": task.assignee_preset_id}
        if task.assignee_user_id is not None:
            return {"type": "user", "user_id": task.assignee_user_id}
        return None

    @staticmethod
    def _actor_summary(actor: TaskActorContext) -> ChannelTaskActorSummary:
        return ChannelTaskActorSummary(
            actor_type="agent" if actor.actor_type == "agent" else "user",
            user_id=actor.actor_user_id if actor.actor_type == "user" else None,
            agent_identity_id=actor.actor_agent_identity_id,
            agent_handle=actor.actor_agent_handle,
            label=actor.actor_label,
        )

    def _user_summary(
        self,
        db: Session,
        user_id: str | None,
    ) -> ChannelTaskActorSummary | None:
        if not user_id:
            return None
        user = UserRepository.get_by_id(db, user_id)
        if not isinstance(user, User):
            return ChannelTaskActorSummary(
                actor_type="user",
                user_id=user_id,
                label=user_id,
            )
        return ChannelTaskActorSummary(
            actor_type="user",
            user_id=user.id,
            label=(user.display_name or user.primary_email or user.id),
            avatar_url=user.avatar_url,
        )

    def _agent_summary(
        self,
        db: Session,
        agent_identity_id: uuid.UUID | None,
        *,
        preset_id: int | None = None,
    ) -> ChannelTaskActorSummary | None:
        if agent_identity_id is not None:
            agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
            if not isinstance(agent, AgentIdentity):
                return ChannelTaskActorSummary(
                    actor_type="agent",
                    agent_identity_id=agent_identity_id,
                    label=str(agent_identity_id),
                )
            return ChannelTaskActorSummary(
                actor_type="agent",
                agent_identity_id=agent.id,
                agent_handle=agent.handle,
                label=agent.display_name or agent.handle or str(agent.id),
                visual_key=agent.visual_key,
            )
        if preset_id is not None:
            return ChannelTaskActorSummary(
                actor_type="agent",
                label=f"Preset {preset_id}",
                visual_key=str(preset_id),
            )
        return None

    def _assignee_summary(
        self,
        db: Session,
        task: ServerChannelTask,
    ) -> ChannelTaskActorSummary | None:
        if task.assignee_agent_identity_id is not None:
            return self._agent_summary(db, task.assignee_agent_identity_id)
        if task.assignee_preset_id is not None:
            return self._agent_summary(db, None, preset_id=task.assignee_preset_id)
        return self._user_summary(db, task.assignee_user_id)

    @staticmethod
    def _summary_payload(
        summary: ChannelTaskActorSummary | None,
    ) -> dict[str, object] | None:
        if summary is None:
            return None
        return summary.model_dump(mode="json", exclude_none=True)

    @staticmethod
    def _actor_label(current_user: User) -> str:
        return (
            current_user.display_name or current_user.primary_email or current_user.id
        )

    def _build_actor_context(
        self,
        current_user: User,
        actor_context: TaskActorContext | None = None,
    ) -> TaskActorContext:
        if actor_context is not None:
            return actor_context
        return TaskActorContext(
            actor_type="user",
            actor_user_id=current_user.id,
            actor_label=self._actor_label(current_user),
        )

    def _require_channel_access(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> ServerChannel:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        if channel.visibility == "private":
            membership = ServerChannelMemberRepository.get_by_channel_and_user(
                db,
                channel.id,
                current_user.id,
            )
            if membership is None or membership.status != "active":
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="You are not a member of this private channel",
                )
        return channel

    def _require_task_access(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> tuple[ServerChannel, ServerChannelTask]:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        task = ServerChannelTaskRepository.get_by_id(db, task_id)
        if task is None or task.server_id != server_id or task.channel_id != channel.id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel task not found: {task_id}",
            )
        return channel, task

    def _validate_user_assignee(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        user_id: str,
    ) -> None:
        membership = ServerMemberRepository.get_by_server_and_user(
            db,
            server_id,
            user_id,
        )
        if membership is None or membership.status != "active":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Task assignee must be an active server member",
            )

    def _validate_agent_assignee(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> None:
        agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent is None or agent.server_id != server_id or agent.removed_at is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Task assignee agent must belong to this server",
            )
        membership = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel_id,
            agent_identity_id,
        )
        if membership is None or membership.status != "active":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Task assignee agent must be an active channel member",
            )

    def _validate_task_assignee(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        assignee_user_id: str | None,
        assignee_agent_identity_id: uuid.UUID | None,
    ) -> None:
        if assignee_user_id is not None:
            self._validate_user_assignee(
                db,
                server_id=server_id,
                user_id=assignee_user_id,
            )
        if assignee_agent_identity_id is not None:
            self._validate_agent_assignee(
                db,
                server_id=server_id,
                channel_id=channel_id,
                agent_identity_id=assignee_agent_identity_id,
            )

    def _next_display_number(self, db: Session, channel_id: uuid.UUID) -> int:
        current_max = ServerChannelTaskRepository.get_max_display_number(db, channel_id)
        return (current_max or 0) + 1

    @staticmethod
    def _assignee_key(task: ServerChannelTask) -> tuple[str, str] | None:
        if task.assignee_user_id is not None:
            return ("user", task.assignee_user_id)
        if task.assignee_agent_identity_id is not None:
            return ("agent", str(task.assignee_agent_identity_id))
        if task.assignee_preset_id is not None:
            return ("preset", str(task.assignee_preset_id))
        return None

    def _summary_from_key(
        self,
        db: Session,
        assignee_key: tuple[str, str] | None,
    ) -> ChannelTaskActorSummary | None:
        if assignee_key is None:
            return None
        assignee_type, value = assignee_key
        if assignee_type == "user":
            return self._user_summary(db, value)
        if assignee_type == "agent":
            return self._agent_summary(db, uuid.UUID(value))
        if assignee_type == "preset":
            return self._agent_summary(db, None, preset_id=int(value))
        return None

    @staticmethod
    def _assignee_event_type(
        before: tuple[str, str] | None,
        after: tuple[str, str] | None,
    ) -> str | None:
        if before == after:
            return None
        if before is None and after is not None:
            return "task.assigned"
        if before is not None and after is None:
            return "task.unassigned"
        return "task.reassigned"

    def _create_assignee_change_event(
        self,
        db: Session,
        *,
        current_user: User,
        task: ServerChannelTask,
        before: tuple[str, str] | None,
        after: tuple[str, str] | None,
        actor_context: TaskActorContext | None = None,
    ) -> None:
        event_type = self._assignee_event_type(before, after)
        if event_type is None:
            return
        actor = self._build_actor_context(current_user, actor_context)
        if event_type == "task.unassigned":
            text_preview = f"{actor.actor_label} unassigned task #{task.display_number}"
        else:
            assignee = self._summary_from_key(db, after)
            label = assignee.label if assignee is not None else "assignee"
            text_preview = (
                f"{actor.actor_label} assigned task #{task.display_number} to {label}"
            )
        self._create_system_message(
            db,
            current_user=current_user,
            task=task,
            event=event_type,
            text_preview=text_preview,
            extra_content={
                "from_assignee": self._summary_payload(
                    self._summary_from_key(db, before)
                ),
                "to_assignee": self._summary_payload(self._summary_from_key(db, after)),
            },
            actor_context=actor_context,
        )

    def _move_task_within_channel(
        self,
        db: Session,
        task: ServerChannelTask,
        *,
        target_status: str,
        target_position: int,
    ) -> None:
        self._validate_status(target_status)

        if task.status == target_status:
            column_tasks = ServerChannelTaskRepository.list_by_channel_and_status(
                db,
                task.channel_id,
                target_status,
                exclude_task_id=task.id,
            )
            insert_at = self._normalize_position(target_position, len(column_tasks))
            column_tasks.insert(insert_at, task)
            self._resequence_tasks(column_tasks, target_status)
            return

        source_status = task.status
        source_tasks = ServerChannelTaskRepository.list_by_channel_and_status(
            db,
            task.channel_id,
            source_status,
            exclude_task_id=task.id,
        )
        target_tasks = ServerChannelTaskRepository.list_by_channel_and_status(
            db,
            task.channel_id,
            target_status,
            exclude_task_id=task.id,
        )
        insert_at = self._normalize_position(target_position, len(target_tasks))
        target_tasks.insert(insert_at, task)
        self._resequence_tasks(source_tasks, source_status)
        self._resequence_tasks(target_tasks, target_status)

    def _create_message(
        self,
        db: Session,
        *,
        channel_id: uuid.UUID,
        author_user_id: str | None,
        message_type: str,
        content: dict[str, object],
        text_preview: str,
        thread_root_message_id: uuid.UUID | None = None,
    ) -> ServerChannelMessage:
        message = ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel_id,
                author_user_id=author_user_id,
                message_type=message_type,
                content=content,
                text_preview=text_preview,
                thread_root_message_id=thread_root_message_id,
            ),
        )
        db.flush()
        return message

    def _task_event_content(
        self,
        db: Session,
        *,
        task: ServerChannelTask,
        event_type: str,
        actor: TaskActorContext,
        extra_content: dict[str, object] | None = None,
    ) -> dict[str, object]:
        actor_summary = self._actor_summary(actor)
        content: dict[str, object] = {
            "event_type": event_type,
            "event": event_type,
            "task_id": str(task.id),
            "task_number": task.display_number,
            "task_title": task.title,
            "title": task.title,
            "status": task.status,
            "actor": self._summary_payload(actor_summary),
            "actor_type": actor_summary.actor_type,
            "actor_label": actor_summary.label,
            "actor_user_id": actor_summary.user_id,
            "actor_agent_identity_id": str(actor_summary.agent_identity_id)
            if actor_summary.agent_identity_id
            else None,
            "actor_agent_handle": actor_summary.agent_handle,
            "actor_session_id": str(actor.actor_session_id)
            if actor.actor_session_id
            else None,
            "assignee": self._summary_payload(self._assignee_summary(db, task)),
        }
        if extra_content:
            content.update(extra_content)
        return content

    def _create_task_root_message(
        self,
        db: Session,
        *,
        current_user: User,
        task: ServerChannelTask,
        actor_context: TaskActorContext | None = None,
        source_message_id: uuid.UUID | None = None,
        thread_root_message_id: uuid.UUID | None = None,
    ) -> ServerChannelMessage:
        actor = self._build_actor_context(current_user, actor_context)
        return self._create_message(
            db,
            channel_id=task.channel_id,
            author_user_id=None,
            message_type="event",
            text_preview=f"{actor.actor_label} created task #{task.display_number}",
            content=self._task_event_content(
                db,
                task=task,
                event_type="task.created",
                actor=actor,
                extra_content={
                    "priority": task.priority,
                    "description": task.description,
                    "creator_user_id": current_user.id,
                    "source_message_id": str(source_message_id)
                    if source_message_id
                    else None,
                },
            ),
            thread_root_message_id=thread_root_message_id,
        )

    def _create_system_message(
        self,
        db: Session,
        *,
        current_user: User,
        task: ServerChannelTask,
        event: str,
        text_preview: str,
        extra_content: dict[str, object] | None = None,
        actor_context: TaskActorContext | None = None,
    ) -> None:
        if task.thread_root_message_id is None:
            return
        actor = self._build_actor_context(current_user, actor_context)
        self._create_message(
            db,
            channel_id=task.channel_id,
            author_user_id=None,
            message_type="event",
            text_preview=text_preview,
            content=self._task_event_content(
                db,
                task=task,
                event_type=event,
                actor=actor,
                extra_content=extra_content,
            ),
            thread_root_message_id=task.thread_root_message_id,
        )

    def _resolve_task_thread_root_message_id(
        self,
        db: Session,
        *,
        channel_id: uuid.UUID,
        source_message_id: uuid.UUID | None,
        source_thread_root_message_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        root_message_id = source_thread_root_message_id
        if root_message_id is None and source_message_id is not None:
            source_message = ServerChannelMessageRepository.get_by_id(
                db,
                source_message_id,
            )
            if source_message is None or source_message.channel_id != channel_id:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Task source message is invalid",
                )
            return source_message.thread_root_message_id or source_message.id

        if root_message_id is None:
            return None

        root_message = ServerChannelMessageRepository.get_by_id(db, root_message_id)
        if root_message is None or root_message.channel_id != channel_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Task source thread is invalid",
            )
        return root_message.thread_root_message_id or root_message.id

    def create_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        request: ServerChannelTaskCreateRequest,
        *,
        actor_context: TaskActorContext | None = None,
        source_thread_root_message_id: uuid.UUID | None = None,
    ) -> ServerChannelTaskResponse:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        self._validate_status(request.status)
        self._validate_task_assignee(
            db,
            server_id=server_id,
            channel_id=channel.id,
            assignee_user_id=request.assignee_user_id,
            assignee_agent_identity_id=request.assignee_agent_identity_id,
        )
        activity_thread_root_message_id = self._resolve_task_thread_root_message_id(
            db,
            channel_id=channel.id,
            source_message_id=request.source_message_id,
            source_thread_root_message_id=source_thread_root_message_id,
        )

        sibling_tasks = ServerChannelTaskRepository.list_by_channel_and_status(
            db,
            channel.id,
            request.status,
        )
        target_position = (
            len(sibling_tasks)
            if request.position is None
            else self._normalize_position(request.position, len(sibling_tasks))
        )
        task = ServerChannelTask(
            server_id=server_id,
            channel_id=channel.id,
            display_number=self._next_display_number(db, channel.id),
            title=request.title.strip(),
            description=(request.description or "").strip() or None,
            status=request.status,
            position=target_position,
            priority=request.priority,
            due_date=request.due_date,
            assignee_user_id=request.assignee_user_id,
            assignee_preset_id=request.assignee_preset_id,
            assignee_agent_identity_id=request.assignee_agent_identity_id,
            reporter_user_id=request.reporter_user_id,
            related_project_id=request.related_project_id,
            creator_user_id=current_user.id,
            updated_by=current_user.id,
        )
        task = ServerChannelTaskRepository.create(db, task)
        sibling_tasks.insert(target_position, task)
        self._resequence_tasks(sibling_tasks, request.status)
        db.flush()

        root_message = self._create_task_root_message(
            db,
            current_user=current_user,
            task=task,
            actor_context=actor_context,
            source_message_id=request.source_message_id,
            thread_root_message_id=activity_thread_root_message_id,
        )
        task.thread_root_message_id = activity_thread_root_message_id or root_message.id

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)

    def list_tasks(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[ServerChannelTaskResponse]:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        tasks = ServerChannelTaskRepository.list_by_channel(db, channel.id)
        return [self._build_task_response(db, item) for item in tasks]

    def get_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        return self._build_task_response(db, task)

    def update_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
        request: ServerChannelTaskUpdateRequest,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        before_assignee = self._assignee_key(task)
        changed_fields: list[str] = []
        if "title" in request.model_fields_set and request.title is not None:
            new_title = request.title.strip()
            if task.title != new_title:
                task.title = new_title
                changed_fields.append("title")
        if "description" in request.model_fields_set:
            description = (request.description or "").strip() or None
            if task.description != description:
                task.description = description
                changed_fields.append("description")
        if "priority" in request.model_fields_set:
            if task.priority != request.priority:
                task.priority = request.priority
                changed_fields.append("priority")
        if "due_date" in request.model_fields_set:
            if task.due_date != request.due_date:
                task.due_date = request.due_date
                changed_fields.append("due_date")
        if (
            "assignee_user_id" in request.model_fields_set
            or "assignee_preset_id" in request.model_fields_set
            or "assignee_agent_identity_id" in request.model_fields_set
        ):
            self._validate_task_assignee(
                db,
                server_id=server_id,
                channel_id=channel_id,
                assignee_user_id=request.assignee_user_id,
                assignee_agent_identity_id=request.assignee_agent_identity_id,
            )
            task.assignee_user_id = request.assignee_user_id
            task.assignee_preset_id = request.assignee_preset_id
            task.assignee_agent_identity_id = request.assignee_agent_identity_id
        if "reporter_user_id" in request.model_fields_set:
            task.reporter_user_id = request.reporter_user_id
        if "related_project_id" in request.model_fields_set:
            task.related_project_id = request.related_project_id
        task.updated_by = current_user.id
        after_assignee = self._assignee_key(task)

        if before_assignee != after_assignee:
            self._create_assignee_change_event(
                db,
                current_user=current_user,
                task=task,
                before=before_assignee,
                after=after_assignee,
            )
        if changed_fields:
            actor = self._build_actor_context(current_user)
            self._create_system_message(
                db,
                current_user=current_user,
                task=task,
                event="task.updated",
                text_preview=(
                    f"{actor.actor_label} updated task #{task.display_number}"
                ),
                extra_content={"changed_fields": changed_fields},
            )

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)

    def update_task_status(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
        request: ServerChannelTaskStatusUpdateRequest,
        *,
        actor_context: TaskActorContext | None = None,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        actor = self._build_actor_context(current_user, actor_context)
        previous_status = task.status
        previous_position = task.position
        self._move_task_within_channel(
            db,
            task,
            target_status=request.status,
            target_position=request.position,
        )
        task.updated_by = current_user.id

        if previous_status != task.status:
            self._create_system_message(
                db,
                current_user=current_user,
                task=task,
                event="task.status_changed",
                text_preview=(
                    f"{actor.actor_label} moved task to {task.status.replace('_', ' ')}"
                ),
                extra_content={
                    "from_status": previous_status,
                    "to_status": task.status,
                    "from_position": previous_position,
                    "to_position": task.position,
                },
                actor_context=actor_context,
            )

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)

    def claim_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
        request: ServerChannelTaskClaimRequest,
        *,
        actor_context: TaskActorContext | None = None,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        before_assignee = self._assignee_key(task)
        assignee_user_id = request.assignee_user_id or current_user.id
        assignee_preset_id = request.assignee_preset_id
        assignee_agent_identity_id = request.assignee_agent_identity_id
        if assignee_preset_id is not None:
            assignee_user_id = None
        if assignee_agent_identity_id is not None:
            assignee_user_id = None
            assignee_preset_id = None
        if (
            actor_context is not None
            and actor_context.actor_type == "agent"
            and request.assignee_user_id is None
            and request.assignee_preset_id is None
            and request.assignee_agent_identity_id is None
        ):
            assignee_user_id = None
            assignee_preset_id = None
            assignee_agent_identity_id = actor_context.actor_agent_identity_id
        self._validate_task_assignee(
            db,
            server_id=server_id,
            channel_id=channel_id,
            assignee_user_id=assignee_user_id,
            assignee_agent_identity_id=assignee_agent_identity_id,
        )
        task.assignee_user_id = assignee_user_id
        task.assignee_preset_id = assignee_preset_id
        task.assignee_agent_identity_id = assignee_agent_identity_id
        task.updated_by = current_user.id

        self._create_assignee_change_event(
            db,
            current_user=current_user,
            task=task,
            before=before_assignee,
            after=self._assignee_key(task),
            actor_context=actor_context,
        )

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)

    def unclaim_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
        *,
        actor_context: TaskActorContext | None = None,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        before_assignee = self._assignee_key(task)
        task.assignee_user_id = None
        task.assignee_preset_id = None
        task.assignee_agent_identity_id = None
        task.updated_by = current_user.id

        self._create_assignee_change_event(
            db,
            current_user=current_user,
            task=task,
            before=before_assignee,
            after=None,
            actor_context=actor_context,
        )

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)

    def comment_on_task(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        task_id: uuid.UUID,
        text: str,
        *,
        actor_context: TaskActorContext | None = None,
    ) -> ServerChannelTaskResponse:
        _, task = self._require_task_access(
            db,
            current_user,
            server_id,
            channel_id,
            task_id,
        )
        task.updated_by = current_user.id

        self._create_system_message(
            db,
            current_user=current_user,
            task=task,
            event="task.commented",
            text_preview=text.strip()[:200] or "Task commented",
            extra_content={"comment_text": text.strip()},
            actor_context=actor_context,
        )

        db.commit()
        db.refresh(task)
        return self._build_task_response(db, task)
