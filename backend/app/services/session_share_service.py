import logging
import secrets
import uuid
from collections.abc import Sequence
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
from app.repositories.user_repository import UserRepository
from app.schemas.message import MessageResponse
from app.schemas.server_channel_message import (
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.session_share import (
    ConversationTimelineItem,
    SessionShareCreateRequest,
    SessionShareForkResponse,
    SessionSharePublicResponse,
    SessionShareSnapshotResponse,
    SessionShareToChannelRequest,
    SessionShareToChannelResponse,
    SharedRunSummary,
    SharedSessionSummary,
    SharedToolExecution,
)
from app.schemas.callback import FileChange
from app.schemas.workspace import FileNode
from app.services.channel_artifact_service import ChannelArtifactService
from app.services.server_channel_access import require_channel_member_access
from app.services.storage_service import S3StorageService
from app.services.server_channel_event_service import (
    ChannelEventActor,
    ChannelEventTarget,
    create_channel_event_message,
)
from app.utils.computer import build_browser_screenshot_key
from app.utils.workspace_export import build_workspace_file_nodes_from_export

JsonValueT = TypeVar("JsonValueT")
logger = logging.getLogger(__name__)
storage_service = S3StorageService()
channel_artifact_service = ChannelArtifactService()


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
    def _extract_text_from_json(value: object) -> str:
        fragments: list[str] = []

        def visit(node: object) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return
            if not isinstance(node, dict):
                return

            for key in ("text", "result"):
                raw_text = node.get(key)
                if isinstance(raw_text, str) and raw_text.strip():
                    fragments.append(raw_text.strip())

            for key in ("message", "content"):
                nested = node.get(key)
                if isinstance(nested, dict | list):
                    visit(nested)

        visit(value)
        return "\n\n".join(fragments).strip()

    @classmethod
    def _extract_message_text(cls, message: AgentMessage | MessageResponse) -> str:
        content_text = cls._extract_text_from_json(message.content)
        if content_text:
            return content_text

        preview = (message.text_preview or "").strip()
        if preview and preview.lower() not in {"user", "assistant", "system"}:
            return preview

        return ""

    @staticmethod
    def _truncate_label(value: str, *, limit: int = 120) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1].rstrip()}..."

    @staticmethod
    def _resolve_user_label(db: Session, user_id: str) -> str:
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            return user_id
        for raw_value in (user.display_name, user.primary_email, user.id):
            if isinstance(raw_value, str) and raw_value.strip():
                return raw_value.strip()
        return user_id

    @staticmethod
    def _extract_workspace_state_from_state_patch(
        state_patch: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(state_patch, dict):
            return {}
        workspace_state = state_patch.get("workspace_state") or state_patch.get(
            "workspaceState"
        )
        if not isinstance(workspace_state, dict):
            return {}
        return workspace_state

    @classmethod
    def _extract_workspace_state(cls, run: AgentRun) -> dict[str, Any]:
        state_patch = run.state_patch if isinstance(run.state_patch, dict) else {}
        return cls._extract_workspace_state_from_state_patch(state_patch)

    @staticmethod
    def _coerce_int(value: object, default: int = 0) -> int:
        return value if isinstance(value, int) else default

    @classmethod
    def _resolve_file_changes_from_workspace_state(
        cls,
        workspace_state: dict[str, Any],
    ) -> list[FileChange]:
        file_changes = workspace_state.get("file_changes") or workspace_state.get(
            "fileChanges"
        )
        if not isinstance(file_changes, list):
            return []

        changes_by_path: dict[str, FileChange] = {}
        for item in file_changes:
            if not isinstance(item, dict):
                continue
            raw_path = item.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            raw_status = item.get("status")
            raw_old_path = item.get("old_path") or item.get("oldPath")
            raw_diff = item.get("diff")
            path = raw_path.strip()
            changes_by_path[path] = FileChange(
                path=path,
                status=raw_status
                if isinstance(raw_status, str) and raw_status.strip()
                else "modified",
                added_lines=cls._coerce_int(
                    item.get("added_lines") or item.get("addedLines")
                ),
                deleted_lines=cls._coerce_int(
                    item.get("deleted_lines") or item.get("deletedLines")
                ),
                diff=raw_diff if isinstance(raw_diff, str) else None,
                old_path=raw_old_path if isinstance(raw_old_path, str) else None,
            )
        return list(changes_by_path.values())

    @classmethod
    def _resolve_file_changes(cls, run: AgentRun) -> list[FileChange]:
        return cls._resolve_file_changes_from_workspace_state(
            cls._extract_workspace_state(run)
        )

    @classmethod
    def _resolve_file_change_count(
        cls,
        run: AgentRun,
        file_changes: list[FileChange] | None = None,
    ) -> int:
        workspace_state = cls._extract_workspace_state(run)
        raw_count = workspace_state.get("file_change_count") or workspace_state.get(
            "fileChangeCount"
        )
        if isinstance(raw_count, int) and raw_count > 0:
            return raw_count

        resolved_file_changes = file_changes or cls._resolve_file_changes(run)
        return len({change.path for change in resolved_file_changes if change.path})

    @classmethod
    def _build_tool_execution_snapshots(
        cls,
        db: Session,
        run: AgentRun,
    ) -> list[SharedToolExecution]:
        return cls._build_shared_tool_executions_from_run_id(db, run.id)

    @classmethod
    def _build_run_summary(
        cls,
        db: Session,
        run: AgentRun,
        *,
        replay_step_count: int,
    ) -> SharedRunSummary:
        file_changes = cls._resolve_file_changes(run)
        return SharedRunSummary(
            run_id=run.id,
            user_message_id=run.user_message_id,
            status=run.status,
            progress=run.progress,
            schedule_mode=run.schedule_mode,
            workspace_export_status=run.workspace_export_status,
            replay_step_count=replay_step_count,
            file_change_count=cls._resolve_file_change_count(run, file_changes),
            file_changes=file_changes,
            tool_executions=cls._build_tool_execution_snapshots(db, run),
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

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
            cls._build_run_summary(
                db,
                run,
                replay_step_count=replay_counts_by_run_id.get(run.id, 0),
            )
            for run in runs
        ]

    @classmethod
    def _build_shared_tool_executions_from_run_id(
        cls,
        db: Session,
        run_id: uuid.UUID,
    ) -> list[SharedToolExecution]:
        return [
            SharedToolExecution(
                id=execution.id,
                run_id=execution.run_id,
                message_id=execution.message_id,
                tool_use_id=execution.tool_use_id,
                tool_name=execution.tool_name,
                tool_input=execution.tool_input,
                tool_output=execution.tool_output,
                is_error=execution.is_error,
                duration_ms=execution.duration_ms,
                created_at=execution.created_at,
                updated_at=execution.updated_at,
            )
            for execution in ToolExecutionRepository.list_by_run(db, run_id, limit=250)
        ]

    @staticmethod
    def _coerce_non_empty_string(value: object) -> str | None:
        return value if isinstance(value, str) and value.strip() else None

    @classmethod
    def _extract_string_field(cls, payload: dict[str, Any], key: str) -> str | None:
        return cls._coerce_non_empty_string(payload.get(key))

    @staticmethod
    def _tool_execution_needs_browser_screenshot(
        execution: dict[str, Any],
    ) -> bool:
        tool_name = execution.get("tool_name")
        return isinstance(tool_name, str) and tool_name.startswith(
            "mcp____poco_playwright__"
        )

    @classmethod
    def _build_browser_screenshot_url(
        cls,
        *,
        owner_user_id: str,
        session_id: uuid.UUID,
        run_id: uuid.UUID | None,
        tool_use_id: str,
    ) -> str | None:
        key = ""
        if run_id is not None:
            key = build_browser_screenshot_key(
                user_id=owner_user_id,
                session_id=str(session_id),
                run_id=str(run_id),
                tool_use_id=tool_use_id,
            )

        try:
            if not key or not storage_service.exists(key):
                legacy_key = build_browser_screenshot_key(
                    user_id=owner_user_id,
                    session_id=str(session_id),
                    tool_use_id=tool_use_id,
                )
                key = legacy_key if storage_service.exists(legacy_key) else ""
            if not key:
                return None
            return storage_service.presign_get(
                key,
                response_content_disposition="inline",
                response_content_type="image/png",
            )
        except Exception:
            logger.exception("Failed to build shared browser screenshot URL")
            return None

    @classmethod
    def _attach_public_browser_screenshot_urls(
        cls,
        executions: list[dict[str, Any]],
        *,
        owner_user_id: str,
        session_id: uuid.UUID,
        run_id: uuid.UUID | None,
    ) -> None:
        for execution in executions:
            if not cls._tool_execution_needs_browser_screenshot(execution):
                continue
            tool_use_id = cls._coerce_non_empty_string(execution.get("tool_use_id"))
            if not tool_use_id:
                continue
            execution["browser_screenshot_url"] = cls._build_browser_screenshot_url(
                owner_user_id=owner_user_id,
                session_id=session_id,
                run_id=run_id,
                tool_use_id=tool_use_id,
            )

    @classmethod
    def _build_workspace_files_for_public_run(
        cls,
        db: Session,
        *,
        fork_run: dict[str, Any] | None,
        source_run_id: uuid.UUID | None,
    ) -> list[FileNode]:
        manifest_key = (
            cls._extract_string_field(fork_run, "workspace_manifest_key")
            if isinstance(fork_run, dict)
            else None
        )
        workspace_files_prefix = (
            cls._extract_string_field(fork_run, "workspace_files_prefix")
            if isinstance(fork_run, dict)
            else None
        )

        if not manifest_key and source_run_id is not None:
            source_run = RunRepository.get_by_id(db, source_run_id)
            if source_run is not None:
                manifest_key = cls._coerce_non_empty_string(
                    source_run.workspace_manifest_key
                )
                workspace_files_prefix = cls._coerce_non_empty_string(
                    source_run.workspace_files_prefix
                )

        return build_workspace_file_nodes_from_export(
            manifest_key=manifest_key,
            workspace_files_prefix=workspace_files_prefix,
            storage_service=storage_service,
        )

    @classmethod
    def _resolve_share_workspace_export(
        cls,
        payload: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        candidates: list[dict[str, Any]] = []
        fork_session = payload.get("fork_session")
        if isinstance(fork_session, dict):
            candidates.append(fork_session)
        fork_runs = payload.get("fork_runs")
        if isinstance(fork_runs, list):
            candidates.extend(
                item for item in reversed(fork_runs) if isinstance(item, dict)
            )

        for candidate in candidates:
            manifest_key = cls._extract_string_field(
                candidate,
                "workspace_manifest_key",
            )
            workspace_files_prefix = cls._extract_string_field(
                candidate,
                "workspace_files_prefix",
            )
            if manifest_key and workspace_files_prefix:
                return manifest_key, workspace_files_prefix
        return None, None

    @classmethod
    def _build_public_run_snapshots(
        cls,
        db: Session,
        payload: dict[str, Any],
        *,
        share: SessionShare,
    ) -> list[SharedRunSummary]:
        raw_runs = payload.get("runs", [])
        if not isinstance(raw_runs, list):
            return []

        fork_runs_by_id = {
            str(item.get("run_id")): item
            for item in payload.get("fork_runs", [])
            if isinstance(item, dict) and item.get("run_id")
        }
        summaries: list[SharedRunSummary] = []
        for raw_run in raw_runs:
            if not isinstance(raw_run, dict):
                continue

            run_payload = dict(raw_run)
            source_run_id = cls._parse_snapshot_uuid(run_payload.get("run_id"))
            fork_run = fork_runs_by_id.get(str(run_payload.get("run_id")))
            if not isinstance(run_payload.get("file_changes"), list) and isinstance(
                fork_run, dict
            ):
                workspace_state = cls._extract_workspace_state_from_state_patch(
                    fork_run.get("state_patch")
                    if isinstance(fork_run.get("state_patch"), dict)
                    else None
                )
                file_changes = cls._resolve_file_changes_from_workspace_state(
                    workspace_state
                )
                run_payload["file_changes"] = [
                    change.model_dump(mode="json") for change in file_changes
                ]
                raw_count = run_payload.get("file_change_count")
                if not isinstance(raw_count, int) or raw_count <= 0:
                    run_payload["file_change_count"] = len(file_changes)

            raw_tool_executions = run_payload.get("tool_executions")
            replay_step_count = run_payload.get("replay_step_count")
            should_refresh_tool_executions = not isinstance(raw_tool_executions, list)
            if isinstance(raw_tool_executions, list):
                should_refresh_tool_executions = (
                    isinstance(replay_step_count, int)
                    and replay_step_count > 0
                    and len(raw_tool_executions) == 0
                ) or any(
                    not isinstance(item, dict) or "tool_output" not in item
                    for item in raw_tool_executions
                )
            if source_run_id is not None and should_refresh_tool_executions:
                tool_executions = [
                    execution.model_dump(mode="json")
                    for execution in cls._build_shared_tool_executions_from_run_id(
                        db,
                        source_run_id,
                    )
                ]
            elif isinstance(raw_tool_executions, list):
                tool_executions = [
                    dict(item) for item in raw_tool_executions if isinstance(item, dict)
                ]
            else:
                tool_executions = []

            cls._attach_public_browser_screenshot_urls(
                tool_executions,
                owner_user_id=share.owner_user_id,
                session_id=share.source_session_id,
                run_id=source_run_id,
            )
            run_payload["tool_executions"] = tool_executions

            workspace_files = cls._build_workspace_files_for_public_run(
                db,
                fork_run=fork_run if isinstance(fork_run, dict) else None,
                source_run_id=source_run_id,
            )
            run_payload["workspace_files"] = [
                node.model_dump(mode="json") for node in workspace_files
            ]

            summaries.append(SharedRunSummary.model_validate(run_payload))
        return summaries

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
                    label=cls._truncate_label(
                        cls._extract_message_text(message) or "Message"
                    ),
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
                        "artifact_references": content.get("artifact_references") or [],
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
    def _snapshot_payload_or_404(share: SessionShare) -> dict[str, Any]:
        payload = share.snapshot_payload
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Share snapshot is not available",
            )
        return payload

    @staticmethod
    def _parse_snapshot_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def _parse_snapshot_uuid(value: object) -> uuid.UUID | None:
        if isinstance(value, uuid.UUID):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return uuid.UUID(value.strip())
        except ValueError:
            return None

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _serialize_run_for_fork(
        self,
        run: AgentRun,
        *,
        share: SessionShare,
    ) -> dict[str, Any]:
        return {
            "run_id": str(run.id),
            "user_message_id": run.user_message_id,
            "status": run.status,
            "permission_mode": run.permission_mode,
            "progress": run.progress,
            "schedule_mode": run.schedule_mode,
            "scheduled_at": self._serialize_datetime(run.scheduled_at),
            "config_snapshot": self._sanitize_config_for_fork(
                run.config_snapshot,
                share=share,
            ),
            "state_patch": self._deepcopy_json(run.state_patch),
            "attempts": run.attempts,
            "last_error": run.last_error,
            "started_at": self._serialize_datetime(run.started_at),
            "finished_at": self._serialize_datetime(run.finished_at),
            "workspace_archive_url": run.workspace_archive_url,
            "workspace_files_prefix": run.workspace_files_prefix,
            "workspace_manifest_key": run.workspace_manifest_key,
            "workspace_archive_key": run.workspace_archive_key,
            "workspace_export_status": run.workspace_export_status,
        }

    def _serialize_usage_log_for_fork(self, usage_log: UsageLog) -> dict[str, Any]:
        return {
            "run_id": str(usage_log.run_id) if usage_log.run_id is not None else None,
            "duration_ms": usage_log.duration_ms,
            "input_tokens": usage_log.input_tokens,
            "output_tokens": usage_log.output_tokens,
            "cache_creation_input_tokens": usage_log.cache_creation_input_tokens,
            "cache_read_input_tokens": usage_log.cache_read_input_tokens,
            "total_tokens": usage_log.total_tokens,
            "usage_json": self._deepcopy_json(usage_log.usage_json),
        }

    def _build_share_snapshot_payload(
        self,
        db: Session,
        *,
        share: SessionShare,
        source_session: AgentSession,
    ) -> dict[str, Any]:
        messages = MessageRepository.list_by_session(db, source_session.id, limit=1000)
        db_runs = RunRepository.list_by_session(db, source_session.id, limit=1000)
        run_summaries = self._build_run_summaries(db, db_runs)
        timeline = self._build_timeline(messages=messages, runs=run_summaries)
        terminal_runs = [
            run for run in db_runs if run.status in {"completed", "failed", "canceled"}
        ]
        usage_logs = UsageLogRepository.list_by_session(db, source_session.id)

        return {
            "version": 1,
            "session": SharedSessionSummary(
                session_id=source_session.id,
                title=share.title or source_session.title,
                status=source_session.status,
                created_at=source_session.created_at,
                updated_at=source_session.updated_at,
            ).model_dump(mode="json"),
            "messages": [
                MessageResponse.model_validate(message).model_dump(mode="json")
                for message in messages
            ],
            "runs": [run.model_dump(mode="json") for run in run_summaries],
            "timeline": [item.model_dump(mode="json") for item in timeline],
            "fork_session": {
                "title": share.title or source_session.title,
                "status": "completed",
                "config_snapshot": self._sanitize_config_for_fork(
                    source_session.config_snapshot,
                    share=share,
                ),
                "workspace_archive_url": source_session.workspace_archive_url,
                "state_patch": self._deepcopy_json(source_session.state_patch),
                "workspace_files_prefix": source_session.workspace_files_prefix,
                "workspace_manifest_key": source_session.workspace_manifest_key,
                "workspace_archive_key": source_session.workspace_archive_key,
                "workspace_export_status": source_session.workspace_export_status,
            },
            "fork_runs": [
                self._serialize_run_for_fork(run, share=share) for run in terminal_runs
            ],
            "usage_logs": [
                self._serialize_usage_log_for_fork(usage_log)
                for usage_log in usage_logs
            ],
        }

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
                snapshot_payload={},
            ),
        )
        db.flush()
        share.snapshot_payload = self._build_share_snapshot_payload(
            db,
            share=share,
            source_session=source_session,
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
        payload = self._snapshot_payload_or_404(share)
        return SessionShareSnapshotResponse(
            share=SessionSharePublicResponse.model_validate(share),
            session=SharedSessionSummary.model_validate(payload["session"]),
            messages=[
                MessageResponse.model_validate(message)
                for message in payload.get("messages", [])
            ],
            runs=self._build_public_run_snapshots(db, payload, share=share),
            timeline=[
                ConversationTimelineItem.model_validate(item)
                for item in payload.get("timeline", [])
            ],
        )

    def fork_share(
        self,
        db: Session,
        *,
        token: str,
        target_user_id: str,
    ) -> SessionShareForkResponse:
        share = self._active_share_or_404(db, token)
        forked_session = self._clone_session_for_share_fork(
            db,
            share=share,
            target_user_id=target_user_id,
        )
        db.commit()
        db.refresh(forked_session)
        return SessionShareForkResponse(
            session_id=forked_session.id,
            source_session_id=share.source_session_id,
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
        if share.owner_user_id != current_user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Only the share owner can import the session to a channel",
            )
        payload = self._snapshot_payload_or_404(share)
        source_session_summary = SharedSessionSummary.model_validate(payload["session"])
        channel = require_channel_member_access(
            db,
            server_id=request.server_id,
            channel_id=request.channel_id,
            user_id=current_user_id,
        )
        source_messages = [
            MessageResponse.model_validate(message)
            for message in payload.get("messages", [])
        ]
        source_messages = [
            message
            for message in source_messages
            if self._extract_message_text(message).strip()
        ]
        if not source_messages:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Shared session has no visible messages to import",
            )

        title = (
            request.title
            or share.title
            or source_session_summary.title
            or "Shared conversation"
        ).strip()
        root_source_message = self._select_thread_root_message(source_messages)
        source_runs_by_user_message_id = {
            run.user_message_id: run
            for run in (
                SharedRunSummary.model_validate(item)
                for item in payload.get("runs", [])
            )
            if run.status in {"completed", "failed", "canceled"}
        }
        imported_at = datetime.now(timezone.utc).isoformat()
        actor_label = self._resolve_user_label(db, current_user_id)
        workspace_manifest_key, workspace_files_prefix = (
            self._resolve_share_workspace_export(payload)
        )
        shared_artifacts_path = f"/{ChannelArtifactService.SHARED_FOLDER}/{share.id}"
        published_artifact_count = (
            channel_artifact_service.publish_share_workspace_artifacts(
                db,
                server_id=channel.server_id,
                channel_id=channel.id,
                share_id=share.id,
                publisher_user_id=current_user_id,
                workspace_manifest_key=workspace_manifest_key,
                workspace_files_prefix=workspace_files_prefix,
            )
        )

        root = ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel.id,
                author_user_id=current_user_id
                if root_source_message.role == "user"
                else None,
                message_type="user" if root_source_message.role == "user" else "system",
                content=self._build_imported_message_content(
                    share=share,
                    source_session_id=share.source_session_id,
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
                        source_session_id=share.source_session_id,
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
                actor_label=actor_label,
                actor_user_id=current_user_id,
            ),
            target=ChannelEventTarget(target_label=title),
            content={
                "share_id": str(share.id),
                "source_session_id": str(share.source_session_id),
                "root_message_id": str(root.id),
                "imported_message_count": len(source_messages),
                "shared_artifacts_path": shared_artifacts_path,
                "published_artifact_count": published_artifact_count,
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
            source_session_id=share.source_session_id,
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
        source_messages: Sequence[AgentMessage | MessageResponse],
    ) -> AgentMessage | MessageResponse:
        first_user_message = next(
            (message for message in source_messages if message.role == "user"),
            None,
        )
        return first_user_message or source_messages[0]

    def _build_imported_message_content(
        self,
        *,
        share: SessionShare,
        source_session_id: uuid.UUID,
        source_message: AgentMessage | MessageResponse,
        title: str,
        imported_at: str,
        source_run: AgentRun | SharedRunSummary | None,
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
            "source_session_id": str(source_session_id),
            "source_message_id": source_message.id,
            "source_role": source_message.role,
            "title": title,
            "text": text,
            "body": text,
            "imported_at": imported_at,
        }
        if source_run is not None and source_message.role != "user":
            source_run_id = (
                source_run.id if isinstance(source_run, AgentRun) else source_run.run_id
            )
            content["source_run_id"] = str(source_run_id)
            content["execution_status"] = source_run.status
            content["workspace_export_status"] = source_run.workspace_export_status
        return content

    def _clone_session_for_share_fork(
        self,
        db: Session,
        *,
        share: SessionShare,
        target_user_id: str,
    ) -> AgentSession:
        payload = self._snapshot_payload_or_404(share)
        source_messages = [
            MessageResponse.model_validate(message)
            for message in payload.get("messages", [])
        ]
        if not source_messages:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Shared session has no messages to fork",
            )
        fork_session = payload.get("fork_session")
        if not isinstance(fork_session, dict):
            raise AppException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Share fork snapshot is not available",
            )

        forked_session = SessionRepository.create(
            session_db=db,
            user_id=target_user_id,
            config=self._deepcopy_json(fork_session.get("config_snapshot")),
            project_id=None,
            kind="chat",
        )
        db.flush()

        forked_session.title = (
            fork_session.get("title")
            if isinstance(fork_session.get("title"), str)
            else share.title
        )
        forked_session.status = "completed"
        forked_session.workspace_archive_url = (
            fork_session.get("workspace_archive_url")
            if isinstance(fork_session.get("workspace_archive_url"), str)
            else None
        )
        forked_session.state_patch = self._deepcopy_json(
            fork_session.get("state_patch")
        )
        forked_session.workspace_files_prefix = (
            fork_session.get("workspace_files_prefix")
            if isinstance(fork_session.get("workspace_files_prefix"), str)
            else None
        )
        forked_session.workspace_manifest_key = (
            fork_session.get("workspace_manifest_key")
            if isinstance(fork_session.get("workspace_manifest_key"), str)
            else None
        )
        forked_session.workspace_archive_key = (
            fork_session.get("workspace_archive_key")
            if isinstance(fork_session.get("workspace_archive_key"), str)
            else None
        )
        forked_session.workspace_export_status = (
            fork_session.get("workspace_export_status")
            if isinstance(fork_session.get("workspace_export_status"), str)
            else None
        )
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
            source_runs = payload.get("fork_runs", [])
            for source_run in source_runs:
                if not isinstance(source_run, dict):
                    continue
                source_run_id = self._parse_snapshot_uuid(source_run.get("run_id"))
                if source_run_id is None:
                    continue
                source_user_message_id = source_run.get("user_message_id")
                if not isinstance(source_user_message_id, int):
                    continue
                target_user_message_id = message_id_map.get(source_user_message_id)
                if target_user_message_id is None:
                    continue

                forked_run = RunRepository.create(
                    session_db=db,
                    session_id=forked_session.id,
                    user_message_id=target_user_message_id,
                    permission_mode=str(source_run.get("permission_mode") or "default"),
                    schedule_mode=str(source_run.get("schedule_mode") or "immediate"),
                    scheduled_at=self._parse_snapshot_datetime(
                        source_run.get("scheduled_at")
                    ),
                    config_snapshot=self._deepcopy_json(
                        source_run.get("config_snapshot")
                    ),
                )
                forked_run.status = str(source_run.get("status") or "completed")
                progress = source_run.get("progress")
                forked_run.progress = progress if isinstance(progress, int) else 100
                forked_run.state_patch = self._deepcopy_json(
                    source_run.get("state_patch")
                )
                forked_run.scheduled_task_id = None
                forked_run.claimed_by = None
                forked_run.lease_expires_at = None
                attempts = source_run.get("attempts")
                forked_run.attempts = attempts if isinstance(attempts, int) else 0
                forked_run.last_error = (
                    source_run.get("last_error")
                    if isinstance(source_run.get("last_error"), str)
                    else None
                )
                forked_run.started_at = self._parse_snapshot_datetime(
                    source_run.get("started_at")
                )
                forked_run.finished_at = self._parse_snapshot_datetime(
                    source_run.get("finished_at")
                )
                forked_run.workspace_archive_url = (
                    source_run.get("workspace_archive_url")
                    if isinstance(source_run.get("workspace_archive_url"), str)
                    else None
                )
                forked_run.workspace_files_prefix = (
                    source_run.get("workspace_files_prefix")
                    if isinstance(source_run.get("workspace_files_prefix"), str)
                    else None
                )
                forked_run.workspace_manifest_key = (
                    source_run.get("workspace_manifest_key")
                    if isinstance(source_run.get("workspace_manifest_key"), str)
                    else None
                )
                forked_run.workspace_archive_key = (
                    source_run.get("workspace_archive_key")
                    if isinstance(source_run.get("workspace_archive_key"), str)
                    else None
                )
                forked_run.workspace_export_status = (
                    source_run.get("workspace_export_status")
                    if isinstance(source_run.get("workspace_export_status"), str)
                    else None
                )
                db.flush()
                run_id_map[source_run_id] = forked_run.id

        source_usage_logs = payload.get("usage_logs", [])
        for source_log in source_usage_logs:
            if not isinstance(source_log, dict):
                continue
            target_run_id: uuid.UUID | None = None
            source_run_id = self._parse_snapshot_uuid(source_log.get("run_id"))
            if source_run_id is not None:
                target_run_id = run_id_map.get(source_run_id)
                if target_run_id is None:
                    continue
            UsageLogRepository.create(
                session_db=db,
                session_id=forked_session.id,
                run_id=target_run_id,
                duration_ms=source_log.get("duration_ms")
                if isinstance(source_log.get("duration_ms"), int)
                else None,
                input_tokens=source_log.get("input_tokens")
                if isinstance(source_log.get("input_tokens"), int)
                else None,
                output_tokens=source_log.get("output_tokens")
                if isinstance(source_log.get("output_tokens"), int)
                else None,
                cache_creation_input_tokens=source_log.get(
                    "cache_creation_input_tokens"
                )
                if isinstance(source_log.get("cache_creation_input_tokens"), int)
                else None,
                cache_read_input_tokens=source_log.get("cache_read_input_tokens")
                if isinstance(source_log.get("cache_read_input_tokens"), int)
                else None,
                total_tokens=source_log.get("total_tokens")
                if isinstance(source_log.get("total_tokens"), int)
                else None,
                include_in_user_analytics=False,
                usage_json=self._deepcopy_json(source_log.get("usage_json")),
            )

        return forked_session
