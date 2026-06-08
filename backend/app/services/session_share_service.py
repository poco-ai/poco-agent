import secrets
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.server_channel_message import ServerChannelMessage
from app.models.session_share import SessionShare
from app.models.usage_log import UsageLog
from app.repositories.message_repository import MessageRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.session_share_repository import SessionShareRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.schemas.message import MessageResponse
from app.schemas.server_channel_message import (
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.session_share import (
    ConversationTimelineItem,
    SessionShareCreateRequest,
    SessionShareForkResponse,
    SessionShareResponse,
    SessionShareSnapshotResponse,
    SessionShareToChannelRequest,
    SessionShareToChannelResponse,
    SharedRunSummary,
    SharedSessionSummary,
)
from app.services.server_channel_access import require_channel_member_access
from app.services.server_channel_event_service import (
    ChannelEventActor,
    ChannelEventTarget,
    create_channel_event_message,
)

JsonValueT = TypeVar("JsonValueT")


class SessionShareService:
    CHANNEL_RUNTIME_CONFIG_KEYS = {
        "agent_identity_id",
        "agent_runtime_mode",
        "channel_id",
        "channel_projection_message_id",
        "channel_task_id",
        "persistent_runtime_key",
        "queue_item_id",
        "server_id",
        "thread_root_message_id",
        "trigger_context",
        "trigger_message_id",
        "trigger_type",
    }

    @staticmethod
    def _deepcopy_json(value: JsonValueT) -> JsonValueT:
        if isinstance(value, dict | list):
            return deepcopy(value)
        return value

    @classmethod
    def _sanitize_config_for_fork(
        cls,
        config: dict[str, Any] | None,
        *,
        share: SessionShare,
    ) -> dict[str, Any] | None:
        if not isinstance(config, dict):
            return None

        sanitized = deepcopy(config)
        for key in cls.CHANNEL_RUNTIME_CONFIG_KEYS:
            sanitized.pop(key, None)
        sanitized["filesystem_mode"] = "sandbox"
        sanitized["local_mounts"] = []
        sanitized["source_share_id"] = str(share.id)
        sanitized["source_session_id"] = str(share.source_session_id)
        return sanitized

    @staticmethod
    def _extract_message_text(message: AgentMessage) -> str:
        if message.text_preview:
            return message.text_preview

        content = message.content if isinstance(message.content, dict) else {}
        text = content.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

        blocks = content.get("content")
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                block_text = block.get("text")
                if isinstance(block_text, str) and block_text.strip():
                    return block_text.strip()

        return message.role.capitalize()

    @staticmethod
    def _truncate_label(value: str, *, limit: int = 120) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1].rstrip()}..."

    @staticmethod
    def _resolve_file_change_count(run: AgentRun) -> int:
        state_patch = run.state_patch if isinstance(run.state_patch, dict) else {}
        workspace_state = state_patch.get("workspace_state") or state_patch.get(
            "workspaceState"
        )
        if not isinstance(workspace_state, dict):
            return 0

        raw_count = workspace_state.get("file_change_count") or workspace_state.get(
            "fileChangeCount"
        )
        if isinstance(raw_count, int) and raw_count > 0:
            return raw_count

        file_changes = workspace_state.get("file_changes") or workspace_state.get(
            "fileChanges"
        )
        if isinstance(file_changes, list):
            return len(
                {
                    item.get("path")
                    for item in file_changes
                    if isinstance(item, dict) and item.get("path")
                }
            )
        return 0

    @classmethod
    def _build_run_summaries(
        cls,
        db: Session,
        runs: list[AgentRun],
    ) -> list[SharedRunSummary]:
        replay_counts_by_run_id = ToolExecutionRepository.count_by_run_ids(
            db,
            [run.id for run in runs],
        )
        return [
            SharedRunSummary(
                run_id=run.id,
                user_message_id=run.user_message_id,
                status=run.status,
                progress=run.progress,
                schedule_mode=run.schedule_mode,
                workspace_export_status=run.workspace_export_status,
                replay_step_count=replay_counts_by_run_id.get(run.id, 0),
                file_change_count=cls._resolve_file_change_count(run),
                started_at=run.started_at,
                finished_at=run.finished_at,
                created_at=run.created_at,
                updated_at=run.updated_at,
            )
            for run in runs
        ]

    @classmethod
    def _build_timeline(
        cls,
        *,
        messages: list[AgentMessage],
        runs: list[SharedRunSummary],
    ) -> list[ConversationTimelineItem]:
        items: list[ConversationTimelineItem] = []
        for message in messages:
            items.append(
                ConversationTimelineItem(
                    id=f"message:{message.id}",
                    item_type="message",
                    label=cls._truncate_label(cls._extract_message_text(message)),
                    role=message.role,
                    message_id=message.id,
                    created_at=message.created_at,
                )
            )
        for run in runs:
            items.append(
                ConversationTimelineItem(
                    id=f"run:{run.run_id}",
                    item_type="run",
                    label=f"Run {run.status}",
                    status=run.status,
                    message_id=run.user_message_id,
                    run_id=run.run_id,
                    created_at=run.created_at,
                    metadata={
                        "progress": run.progress,
                        "replay_step_count": run.replay_step_count,
                        "file_change_count": run.file_change_count,
                    },
                )
            )
        return sorted(items, key=lambda item: item.created_at)

    @classmethod
    def _build_channel_import_timeline(
        cls,
        *,
        event: ServerChannelMessage,
        thread_messages: list[ServerChannelMessage],
    ) -> list[ConversationTimelineItem]:
        items = [
            ConversationTimelineItem(
                id=f"channel-event:{event.id}",
                item_type="channel_event",
                label=cls._truncate_label(event.text_preview or "Shared conversation"),
                channel_message_id=event.id,
                created_at=event.created_at,
                metadata={
                    "event_type": (event.content or {}).get("event_type"),
                },
            )
        ]
        for message in thread_messages:
            content = message.content if isinstance(message.content, dict) else {}
            source_message_id = content.get("source_message_id")
            source_run_id = content.get("source_run_id")
            items.append(
                ConversationTimelineItem(
                    id=f"channel-message:{message.id}",
                    item_type="channel_message",
                    label=cls._truncate_label(message.text_preview or "Imported turn"),
                    role=content.get("source_role")
                    if isinstance(content.get("source_role"), str)
                    else None,
                    channel_message_id=message.id,
                    source_message_id=source_message_id
                    if isinstance(source_message_id, int)
                    else None,
                    source_run_id=uuid.UUID(str(source_run_id))
                    if source_run_id
                    else None,
                    created_at=message.created_at,
                    metadata={
                        "message_type": message.message_type,
                        "source": content.get("source"),
                        "artifact_references": content.get("artifact_references")
                        or [],
                    },
                )
            )
        return sorted(items, key=lambda item: item.created_at)

    @staticmethod
    def _active_share_or_404(db: Session, token: str) -> SessionShare:
        share = SessionShareRepository.get_active_by_token(db, token)
        if share is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Share link not found",
            )
        return share

    @staticmethod
    def _source_session_or_404(db: Session, share: SessionShare) -> AgentSession:
        source_session = SessionRepository.get_by_id(db, share.source_session_id)
        if source_session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Shared session not found",
            )
        return source_session

    def create_share(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        owner_user_id: str,
        request: SessionShareCreateRequest,
    ) -> SessionShare:
        source_session = SessionRepository.get_by_id(db, session_id)
        if source_session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )
        if source_session.user_id != owner_user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )
        if source_session.kind != "chat":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Only ordinary chat sessions can be shared",
            )

        token = self._generate_unique_token(db)
        share = SessionShareRepository.create(
            db,
            SessionShare(
                source_session_id=source_session.id,
                owner_user_id=owner_user_id,
                token=token,
                title=(request.title or source_session.title or "").strip() or None,
                description=(request.description or "").strip() or None,
            ),
        )
        db.commit()
        db.refresh(share)
        return share

    def _generate_unique_token(self, db: Session) -> str:
        for _ in range(8):
            token = secrets.token_urlsafe(32)
            if SessionShareRepository.get_by_token(db, token) is None:
                return token
        raise AppException(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Unable to allocate share token",
        )

    def get_snapshot(self, db: Session, *, token: str) -> SessionShareSnapshotResponse:
        share = self._active_share_or_404(db, token)
        source_session = self._source_session_or_404(db, share)
        messages = MessageRepository.list_by_session(db, source_session.id, limit=1000)
        db_runs = RunRepository.list_by_session(db, source_session.id, limit=1000)
        run_summaries = self._build_run_summaries(db, db_runs)
        return SessionShareSnapshotResponse(
            share=SessionShareResponse.model_validate(share),
            session=SharedSessionSummary(
                session_id=source_session.id,
                title=share.title or source_session.title,
                status=source_session.status,
                created_at=source_session.created_at,
                updated_at=source_session.updated_at,
            ),
            messages=[MessageResponse.model_validate(message) for message in messages],
            runs=run_summaries,
            timeline=self._build_timeline(messages=messages, runs=run_summaries),
        )

    def fork_share(
        self,
        db: Session,
        *,
        token: str,
        target_user_id: str,
    ) -> SessionShareForkResponse:
        share = self._active_share_or_404(db, token)
        source_session = self._source_session_or_404(db, share)
        forked_session = self._clone_session_for_share_fork(
            db,
            share=share,
            source_session=source_session,
            target_user_id=target_user_id,
        )
        db.commit()
        db.refresh(forked_session)
        return SessionShareForkResponse(
            session_id=forked_session.id,
            source_session_id=source_session.id,
            share_id=share.id,
        )

    def share_to_channel(
        self,
        db: Session,
        *,
        token: str,
        current_user_id: str,
        request: SessionShareToChannelRequest,
    ) -> SessionShareToChannelResponse:
        share = self._active_share_or_404(db, token)
        source_session = self._source_session_or_404(db, share)
        channel = require_channel_member_access(
            db,
            server_id=request.server_id,
            channel_id=request.channel_id,
            user_id=current_user_id,
        )
        source_messages = MessageRepository.list_by_session(
            db,
            source_session.id,
            limit=1000,
        )
        if not source_messages:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Shared session has no messages to import",
            )

        title = (
            request.title
            or share.title
            or source_session.title
            or "Shared conversation"
        ).strip()
        root_source_message = self._select_thread_root_message(source_messages)
        source_runs_by_user_message_id = self._map_runs_by_user_message_id(
            db,
            source_session.id,
        )
        imported_at = datetime.now(timezone.utc).isoformat()

        root = ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel.id,
                author_user_id=current_user_id
                if root_source_message.role == "user"
                else None,
                message_type="user"
                if root_source_message.role == "user"
                else "system",
                content=self._build_imported_message_content(
                    share=share,
                    source_session=source_session,
                    source_message=root_source_message,
                    title=title,
                    imported_at=imported_at,
                    source_run=None,
                ),
                text_preview=self._truncate_label(
                    self._extract_message_text(root_source_message)
                ),
                thread_root_message_id=None,
            ),
        )
        db.flush()

        replies: list[ServerChannelMessage] = []
        latest_user_message_id: int | None = None
        for source_message in source_messages:
            if source_message.id == root_source_message.id:
                if source_message.role == "user":
                    latest_user_message_id = source_message.id
                continue
            if source_message.role == "user":
                latest_user_message_id = source_message.id
            source_run = (
                source_runs_by_user_message_id.get(latest_user_message_id)
                if latest_user_message_id is not None
                else None
            )
            reply = ServerChannelMessageRepository.create(
                db,
                ServerChannelMessage(
                    channel_id=channel.id,
                    author_user_id=current_user_id
                    if source_message.role == "user"
                    else None,
                    message_type="user" if source_message.role == "user" else "system",
                    content=self._build_imported_message_content(
                        share=share,
                        source_session=source_session,
                        source_message=source_message,
                        title=title,
                        imported_at=imported_at,
                        source_run=source_run,
                    ),
                    text_preview=self._truncate_label(
                        self._extract_message_text(source_message)
                    ),
                    thread_root_message_id=root.id,
                ),
            )
            replies.append(reply)
        db.flush()

        event = create_channel_event_message(
            db,
            channel_id=channel.id,
            event_type="conversation.shared",
            actor=ChannelEventActor(
                actor_type="user",
                actor_label=current_user_id,
                actor_user_id=current_user_id,
            ),
            target=ChannelEventTarget(target_label=title),
            content={
                "share_id": str(share.id),
                "source_session_id": str(source_session.id),
                "root_message_id": str(root.id),
                "imported_message_count": len(source_messages),
            },
            text_preview=f"Shared conversation: {title}",
        )
        db.commit()
        db.refresh(root)
        db.refresh(event)
        for reply in replies:
            db.refresh(reply)

        return SessionShareToChannelResponse(
            share_id=share.id,
            source_session_id=source_session.id,
            event=ServerChannelMessageResponse.model_validate(event),
            thread=ServerChannelThreadResponse(
                root=ServerChannelMessageResponse.model_validate(root),
                replies=[
                    ServerChannelMessageResponse.model_validate(reply)
                    for reply in replies
                ],
            ),
            timeline=self._build_channel_import_timeline(
                event=event,
                thread_messages=[root, *replies],
            ),
        )

    @staticmethod
    def _select_thread_root_message(
        source_messages: list[AgentMessage],
    ) -> AgentMessage:
        first_user_message = next(
            (message for message in source_messages if message.role == "user"),
            None,
        )
        return first_user_message or source_messages[0]

    @staticmethod
    def _map_runs_by_user_message_id(
        db: Session,
        session_id: uuid.UUID,
    ) -> dict[int, AgentRun]:
        runs = RunRepository.list_by_session(db, session_id, limit=1000)
        result: dict[int, AgentRun] = {}
        for run in runs:
            if run.status not in {"completed", "failed", "canceled"}:
                continue
            result[run.user_message_id] = run
        return result

    def _build_imported_message_content(
        self,
        *,
        share: SessionShare,
        source_session: AgentSession,
        source_message: AgentMessage,
        title: str,
        imported_at: str,
        source_run: AgentRun | None,
    ) -> dict[str, Any]:
        text = self._extract_message_text(source_message)
        source = (
            "imported_chat_session"
            if source_message.role == "user"
            else "imported_agent_session"
        )
        content: dict[str, Any] = {
            "source": source,
            "source_share_id": str(share.id),
            "source_session_id": str(source_session.id),
            "source_message_id": source_message.id,
            "source_role": source_message.role,
            "title": title,
            "text": text,
            "body": text,
            "imported_at": imported_at,
        }
        if source_run is not None and source_message.role != "user":
            content["source_run_id"] = str(source_run.id)
            content["execution_status"] = source_run.status
            content["workspace_export_status"] = source_run.workspace_export_status
        artifact_references = self._extract_artifact_references(source_message.content)
        if artifact_references:
            content["artifact_references"] = artifact_references
        return content

    @staticmethod
    def _extract_artifact_references(content: object) -> list[dict[str, Any]]:
        if not isinstance(content, dict):
            return []

        references: list[dict[str, Any]] = []
        for key in ("artifacts", "artifact_references", "artifactReferences"):
            raw_items = content.get(key)
            if not isinstance(raw_items, list):
                continue
            for item in raw_items:
                if isinstance(item, dict):
                    references.append(deepcopy(item))

        entities = content.get("entities")
        if isinstance(entities, list):
            for entity in entities:
                if not isinstance(entity, dict) or entity.get("kind") != "artifact":
                    continue
                references.append(deepcopy(entity))
        return references

    def _clone_session_for_share_fork(
        self,
        db: Session,
        *,
        share: SessionShare,
        source_session: AgentSession,
        target_user_id: str,
    ) -> AgentSession:
        source_messages = MessageRepository.list_by_session(
            db,
            source_session.id,
            limit=1000,
        )
        if not source_messages:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Shared session has no messages to fork",
            )

        forked_session = SessionRepository.create(
            session_db=db,
            user_id=target_user_id,
            config=self._sanitize_config_for_fork(
                source_session.config_snapshot,
                share=share,
            ),
            project_id=None,
            kind="chat",
        )
        db.flush()

        forked_session.title = share.title or source_session.title
        forked_session.status = "completed"
        forked_session.workspace_archive_url = source_session.workspace_archive_url
        forked_session.state_patch = self._deepcopy_json(source_session.state_patch)
        forked_session.workspace_files_prefix = source_session.workspace_files_prefix
        forked_session.workspace_manifest_key = source_session.workspace_manifest_key
        forked_session.workspace_archive_key = source_session.workspace_archive_key
        forked_session.workspace_export_status = source_session.workspace_export_status
        forked_session.sdk_session_id = None

        message_id_map: dict[int, int] = {}
        copied_user_message_ids: set[int] = set()
        for source_message in source_messages:
            forked_message = MessageRepository.create(
                session_db=db,
                session_id=forked_session.id,
                role=source_message.role,
                content=self._deepcopy_json(source_message.content),
                text_preview=source_message.text_preview,
            )
            db.flush()
            message_id_map[source_message.id] = forked_message.id
            if source_message.role == "user":
                copied_user_message_ids.add(source_message.id)

        run_id_map: dict[uuid.UUID, uuid.UUID] = {}
        if copied_user_message_ids:
            source_runs = (
                db.query(AgentRun)
                .filter(AgentRun.session_id == source_session.id)
                .filter(AgentRun.user_message_id.in_(copied_user_message_ids))
                .order_by(AgentRun.scheduled_at.asc(), AgentRun.created_at.asc())
                .all()
            )
            for source_run in source_runs:
                if source_run.status not in {"completed", "failed", "canceled"}:
                    continue
                target_user_message_id = message_id_map.get(source_run.user_message_id)
                if target_user_message_id is None:
                    continue

                forked_run = RunRepository.create(
                    session_db=db,
                    session_id=forked_session.id,
                    user_message_id=target_user_message_id,
                    permission_mode=source_run.permission_mode,
                    schedule_mode=source_run.schedule_mode,
                    scheduled_at=source_run.scheduled_at,
                    config_snapshot=self._sanitize_config_for_fork(
                        source_run.config_snapshot,
                        share=share,
                    ),
                )
                forked_run.status = source_run.status
                forked_run.progress = source_run.progress
                forked_run.state_patch = self._deepcopy_json(source_run.state_patch)
                forked_run.scheduled_task_id = None
                forked_run.claimed_by = None
                forked_run.lease_expires_at = None
                forked_run.attempts = source_run.attempts
                forked_run.last_error = source_run.last_error
                forked_run.started_at = source_run.started_at
                forked_run.finished_at = source_run.finished_at
                forked_run.workspace_archive_url = source_run.workspace_archive_url
                forked_run.workspace_files_prefix = source_run.workspace_files_prefix
                forked_run.workspace_manifest_key = source_run.workspace_manifest_key
                forked_run.workspace_archive_key = source_run.workspace_archive_key
                forked_run.workspace_export_status = source_run.workspace_export_status
                db.flush()
                run_id_map[source_run.id] = forked_run.id

        source_usage_logs = (
            db.query(UsageLog)
            .filter(UsageLog.session_id == source_session.id)
            .order_by(UsageLog.created_at.asc())
            .all()
        )
        for source_log in source_usage_logs:
            target_run_id: uuid.UUID | None = None
            if source_log.run_id is not None:
                target_run_id = run_id_map.get(source_log.run_id)
                if target_run_id is None:
                    continue
            UsageLogRepository.create(
                session_db=db,
                session_id=forked_session.id,
                run_id=target_run_id,
                duration_ms=source_log.duration_ms,
                input_tokens=source_log.input_tokens,
                output_tokens=source_log.output_tokens,
                cache_creation_input_tokens=source_log.cache_creation_input_tokens,
                cache_read_input_tokens=source_log.cache_read_input_tokens,
                total_tokens=source_log.total_tokens,
                include_in_user_analytics=False,
                usage_json=self._deepcopy_json(source_log.usage_json),
            )

        return forked_session
