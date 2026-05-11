import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.server_channel_task import ServerChannelTask
from app.models.user import User
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.repositories.server_channel_task_repository import (
    ServerChannelTaskRepository,
)
from app.schemas.server_channel_task import (
    TASK_STATUS_VALUES,
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
    @staticmethod
    def _build_task_response(task: ServerChannelTask) -> ServerChannelTaskResponse:
        return ServerChannelTaskResponse.model_validate(task)

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
        if task.assignee_preset_id is not None:
            return {"type": "agent", "preset_id": task.assignee_preset_id}
        if task.assignee_user_id is not None:
            return {"type": "user", "user_id": task.assignee_user_id}
        return None

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

    def _create_task_root_message(
        self,
        db: Session,
        *,
        current_user: User,
        task: ServerChannelTask,
        actor_context: TaskActorContext | None = None,
        source_thread_root_message_id: uuid.UUID | None = None,
    ) -> ServerChannelMessage:
        actor = self._build_actor_context(current_user, actor_context)
        return self._create_message(
            db,
            channel_id=task.channel_id,
            author_user_id=None,
            message_type="event",
            text_preview=f"Task created: {task.title}",
            content={
                "event_type": "task.created",
                "event": "task.created",
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "description": task.description,
                "creator_user_id": current_user.id,
                "assignee": self._assignee_payload(task),
                "actor_type": actor.actor_type,
                "actor_label": actor.actor_label,
                "actor_user_id": actor.actor_user_id,
                "actor_agent_identity_id": str(actor.actor_agent_identity_id)
                if actor.actor_agent_identity_id
                else None,
                "actor_agent_handle": actor.actor_agent_handle,
                "actor_session_id": str(actor.actor_session_id)
                if actor.actor_session_id
                else None,
                "source_thread_root_message_id": str(source_thread_root_message_id)
                if source_thread_root_message_id
                else None,
            },
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

        content: dict[str, object] = {
            "event_type": event,
            "event": event,
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "actor_user_id": actor.actor_user_id,
            "actor_label": actor.actor_label,
            "actor_type": actor.actor_type,
            "actor_agent_identity_id": str(actor.actor_agent_identity_id)
            if actor.actor_agent_identity_id
            else None,
            "actor_agent_handle": actor.actor_agent_handle,
            "actor_session_id": str(actor.actor_session_id)
            if actor.actor_session_id
            else None,
            "assignee": self._assignee_payload(task),
        }
        if extra_content:
            content.update(extra_content)
        self._create_message(
            db,
            channel_id=task.channel_id,
            author_user_id=None,
            message_type="event",
            text_preview=text_preview,
            content=content,
            thread_root_message_id=task.thread_root_message_id,
        )

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
            title=request.title.strip(),
            description=(request.description or "").strip() or None,
            status=request.status,
            position=target_position,
            priority=request.priority,
            due_date=request.due_date,
            assignee_user_id=request.assignee_user_id,
            assignee_preset_id=request.assignee_preset_id,
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
            source_thread_root_message_id=source_thread_root_message_id,
        )
        task.thread_root_message_id = root_message.id

        db.commit()
        db.refresh(task)
        return self._build_task_response(task)

    def list_tasks(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[ServerChannelTaskResponse]:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        tasks = ServerChannelTaskRepository.list_by_channel(db, channel.id)
        return [self._build_task_response(item) for item in tasks]

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
        return self._build_task_response(task)

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
        if "title" in request.model_fields_set and request.title is not None:
            task.title = request.title.strip()
        if "description" in request.model_fields_set:
            task.description = (request.description or "").strip() or None
        if "priority" in request.model_fields_set:
            task.priority = request.priority
        if "due_date" in request.model_fields_set:
            task.due_date = request.due_date
        if "reporter_user_id" in request.model_fields_set:
            task.reporter_user_id = request.reporter_user_id
        if "related_project_id" in request.model_fields_set:
            task.related_project_id = request.related_project_id
        task.updated_by = current_user.id

        db.commit()
        db.refresh(task)
        return self._build_task_response(task)

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
        return self._build_task_response(task)

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
        assignee_user_id = request.assignee_user_id or current_user.id
        assignee_preset_id = request.assignee_preset_id
        if assignee_preset_id is not None:
            assignee_user_id = None

        actor = self._build_actor_context(current_user, actor_context)
        task.assignee_user_id = assignee_user_id
        task.assignee_preset_id = assignee_preset_id
        task.updated_by = current_user.id

        self._create_system_message(
            db,
            current_user=current_user,
            task=task,
            event="task.claimed",
            text_preview=f"{actor.actor_label} claimed task",
            actor_context=actor_context,
        )

        db.commit()
        db.refresh(task)
        return self._build_task_response(task)

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
        actor = self._build_actor_context(current_user, actor_context)
        task.assignee_user_id = None
        task.assignee_preset_id = None
        task.updated_by = current_user.id

        self._create_system_message(
            db,
            current_user=current_user,
            task=task,
            event="task.unclaimed",
            text_preview=f"{actor.actor_label} unclaimed task",
            actor_context=actor_context,
        )

        db.commit()
        db.refresh(task)
        return self._build_task_response(task)

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
        return self._build_task_response(task)
