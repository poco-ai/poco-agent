import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.server_channel_message import ServerChannelMessage
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.schemas.callback import (
    AgentCallbackRequest,
    CallbackResponse,
    CallbackStatus,
)
from app.services.run_lifecycle_service import RunLifecycleService
from app.services.im import ImEventService
from app.services.agent_assignment_service import AgentAssignmentService
from app.services.channel_artifact_service import ChannelArtifactService
from app.services.pending_skill_creation_service import PendingSkillCreationService
from app.services.persistent_runtime_service import PersistentRuntimeService
from app.services.session_queue_service import SessionQueueService
from app.services.session_service import SessionService
from app.utils.usage import normalize_usage_payload

logger = logging.getLogger(__name__)

run_lifecycle_service = RunLifecycleService()
session_queue_service = SessionQueueService()
session_service = SessionService()
pending_skill_creation_service = PendingSkillCreationService()


class CallbackService:
    """Service layer for processing executor callbacks."""

    def __init__(self) -> None:
        self._run_lifecycle = RunLifecycleService()
        self._session_queue = SessionQueueService()
        self._session_service = SessionService()
        self._im_events = ImEventService()
        self._assignment_service = AgentAssignmentService()
        self._persistent_runtime_service = PersistentRuntimeService()
        self._channel_artifact_service = ChannelArtifactService()

    def _parse_run_id(self, raw_run_id: str | None) -> uuid.UUID | None:
        if not raw_run_id:
            return None
        try:
            return uuid.UUID(raw_run_id)
        except (TypeError, ValueError):
            logger.warning("callback_invalid_run_id", extra={"run_id": raw_run_id})
            return None

    def _resolve_session_and_run(
        self,
        db: Session,
        callback: AgentCallbackRequest,
        run_id: uuid.UUID | None,
    ) -> tuple[AgentSession | None, AgentRun | None]:
        if run_id is not None:
            db_run = RunRepository.get_by_id(db, run_id)
            if db_run is not None:
                db_session = SessionRepository.get_by_id_for_update(
                    db, db_run.session_id
                )
                if db_session is not None:
                    return db_session, db_run

        session_ref = session_service.find_session_by_sdk_id_or_uuid(
            db, callback.session_id
        )
        if session_ref is None:
            return None, None

        db_session = SessionRepository.get_by_id_for_update(db, session_ref.id)
        if db_session is None:
            return None, None

        if self._should_skip_active_run_fallback(callback):
            return db_session, None

        return db_session, RunRepository.get_latest_active_by_session(db, db_session.id)

    def _should_skip_active_run_fallback(
        self,
        callback: AgentCallbackRequest,
    ) -> bool:
        if callback.run_id:
            return False
        if callback.status not in {CallbackStatus.COMPLETED, CallbackStatus.FAILED}:
            return False
        if callback.new_message is not None:
            return False
        if not self._is_final_workspace_export(callback):
            return False

        return True

    def _is_final_workspace_export(self, callback: AgentCallbackRequest) -> bool:
        export_status = (callback.workspace_export_status or "").strip().lower()
        return bool(export_status) and export_status != "pending"

    def _should_apply_workspace_export(
        self,
        db: Session,
        db_session: AgentSession,
        db_run: AgentRun | None,
        callback: AgentCallbackRequest,
    ) -> bool:
        has_workspace_export_payload = any(
            value is not None
            for value in (
                callback.workspace_files_prefix,
                callback.workspace_manifest_key,
                callback.workspace_archive_key,
                callback.workspace_export_status,
            )
        )
        if not has_workspace_export_payload:
            return True
        if db_run is None:
            return True

        export_status = (callback.workspace_export_status or "").strip().lower()
        latest_terminal_run = RunRepository.get_latest_terminal_by_session(
            db, db_session.id
        )
        if latest_terminal_run is None or latest_terminal_run.id == db_run.id:
            return True
        if export_status == "ready" and db_session.workspace_export_status != "ready":
            return True

        logger.info(
            "skip_stale_workspace_export",
            extra={
                "session_id": str(db_session.id),
                "run_id": str(db_run.id),
                "latest_terminal_run_id": str(latest_terminal_run.id),
                "workspace_export_status": callback.workspace_export_status,
            },
        )
        return False

    def _should_preserve_existing_ready_workspace(
        self,
        db_session: AgentSession,
        callback: AgentCallbackRequest,
    ) -> bool:
        has_existing_ready_workspace = (
            db_session.workspace_export_status or ""
        ).strip().lower() == "ready" and any(
            value
            for value in (
                db_session.workspace_files_prefix,
                db_session.workspace_manifest_key,
                db_session.workspace_archive_key,
            )
        )
        if not has_existing_ready_workspace:
            return False

        incoming_export_status = (
            (callback.workspace_export_status or "").strip().lower()
        )
        incoming_workspace_artifacts = any(
            value is not None
            for value in (
                callback.workspace_files_prefix,
                callback.workspace_manifest_key,
                callback.workspace_archive_key,
            )
        )
        return (
            incoming_export_status not in {"", "ready"}
            and not incoming_workspace_artifacts
        )

    def _extract_sdk_session_id_from_message(
        self, message: dict[str, Any]
    ) -> str | None:
        message_type = message.get("_type", "")

        if "ResultMessage" in message_type and isinstance(
            message.get("session_id"), str
        ):
            return message["session_id"]

        if "SystemMessage" in message_type and message.get("subtype") == "init":
            data = message.get("data", {})
            if not isinstance(data, dict):
                return None
            inner = data.get("data")
            if isinstance(inner, dict) and isinstance(inner.get("session_id"), str):
                return inner["session_id"]
            if isinstance(data.get("session_id"), str):
                return data["session_id"]

        return None

    def _extract_role_from_message(self, message: dict[str, Any]) -> str:
        message_type = message.get("_type", "")

        if "AssistantMessage" in message_type:
            return "assistant"
        if "UserMessage" in message_type:
            return "user"
        if "SystemMessage" in message_type:
            return "system"

        logger.warning(
            "unknown_message_type_default_role",
            extra={"message_type": message_type, "default_role": "assistant"},
        )
        return "assistant"

    def _extract_tool_executions(
        self,
        session_db: Session,
        message: dict[str, Any],
        session_id: uuid.UUID,
        run_id: uuid.UUID | None,
        message_id: int,
    ) -> None:
        content = message.get("content", [])
        if not isinstance(content, list):
            return

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("_type", "")

            if "ToolUseBlock" in block_type:
                tool_use_id = block.get("id")
                tool_name = block.get("name")
                tool_input = block.get("input")

                if not tool_use_id or not tool_name:
                    continue

                existing = ToolExecutionRepository.get_by_session_and_tool_use_id(
                    session_db=session_db,
                    session_id=session_id,
                    tool_use_id=tool_use_id,
                )
                if existing:
                    existing.tool_name = tool_name
                    existing.tool_input = tool_input
                    existing.message_id = message_id
                    if run_id is not None and existing.run_id is None:
                        existing.run_id = run_id
                    continue

                ToolExecutionRepository.create(
                    session_db=session_db,
                    session_id=session_id,
                    message_id=message_id,
                    run_id=run_id,
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                )
                continue

            if "ToolResultBlock" not in block_type:
                continue

            tool_use_id = block.get("tool_use_id")
            result_content = block.get("content")
            is_error = block.get("is_error", False)
            if not tool_use_id:
                continue

            tool_output = {"content": result_content}
            existing = ToolExecutionRepository.get_by_session_and_tool_use_id(
                session_db=session_db,
                session_id=session_id,
                tool_use_id=tool_use_id,
            )
            if not existing:
                ToolExecutionRepository.create(
                    session_db=session_db,
                    session_id=session_id,
                    message_id=message_id,
                    run_id=run_id,
                    tool_use_id=tool_use_id,
                    tool_name="unknown",
                    tool_output=tool_output,
                    result_message_id=message_id,
                    is_error=bool(is_error),
                )
                continue

            existing.tool_output = tool_output
            existing.result_message_id = message_id
            existing.is_error = bool(is_error)
            if run_id is not None and existing.run_id is None:
                existing.run_id = run_id

            if existing.duration_ms is None and existing.created_at is not None:
                duration = datetime.now(timezone.utc) - existing.created_at
                existing.duration_ms = int(duration.total_seconds() * 1000)

    def _extract_and_persist_usage(
        self,
        db: Session,
        db_session: AgentSession,
        db_run: AgentRun | None,
        message: dict[str, Any],
    ) -> None:
        message_type = message.get("_type", "")
        if "ResultMessage" not in message_type:
            return

        usage_data = message.get("usage")
        if not usage_data or not isinstance(usage_data, dict):
            return

        duration_ms = message.get("duration_ms")
        normalized_usage = normalize_usage_payload(usage_data)

        UsageLogRepository.create(
            session_db=db,
            session_id=db_session.id,
            run_id=db_run.id if db_run else None,
            duration_ms=duration_ms,
            input_tokens=normalized_usage["input_tokens"],
            output_tokens=normalized_usage["output_tokens"],
            cache_creation_input_tokens=normalized_usage["cache_creation_input_tokens"],
            cache_read_input_tokens=normalized_usage["cache_read_input_tokens"],
            total_tokens=normalized_usage["total_tokens"],
            include_in_user_analytics=True,
            usage_json=usage_data,
        )

    def _build_execution_summary_from_callback(
        self,
        callback: AgentCallbackRequest,
    ) -> str | None:
        if callback.new_message and isinstance(callback.new_message, dict):
            text = _extract_visible_message_text(callback.new_message)
            if text:
                return text[:280]
        if callback.error_message:
            return callback.error_message[:280]
        return None

    def _build_full_visible_text_from_callback(
        self,
        callback: AgentCallbackRequest,
    ) -> str | None:
        if callback.new_message and isinstance(callback.new_message, dict):
            text = _extract_visible_message_text(callback.new_message)
            if text:
                return text
        if callback.error_message:
            return callback.error_message
        return None

    def _latest_channel_projectable_assistant_message(
        self,
        db: Session,
        session_id: uuid.UUID,
    ) -> AgentMessage | None:
        messages = (
            db.query(AgentMessage)
            .filter(
                AgentMessage.session_id == session_id,
                AgentMessage.role == "assistant",
            )
            .order_by(AgentMessage.id.desc())
            .limit(20)
            .all()
        )
        fallback: AgentMessage | None = None
        for message in messages:
            content = message.content if isinstance(message.content, dict) else {}
            text = (
                _extract_visible_message_text(content)
                or (message.text_preview or "").strip()
            )
            if not text:
                continue
            if fallback is None:
                fallback = message
            message_type = str(content.get("_type", "")).strip()
            if "ResultMessage" not in message_type:
                return message
        return fallback

    def _resolve_server_channel_projection_context(
        self,
        *,
        db_session: AgentSession,
        db_run: AgentRun | None = None,
    ) -> dict[str, uuid.UUID | None]:
        snapshot = (
            db_run.config_snapshot
            if db_run is not None and isinstance(db_run.config_snapshot, dict)
            else db_session.config_snapshot
        ) or {}
        if not isinstance(snapshot, dict):
            snapshot = {}

        def parse_uuid(value) -> uuid.UUID | None:
            if value is None:
                return None
            try:
                return uuid.UUID(str(value))
            except (TypeError, ValueError):
                return None

        return {
            "channel_id": parse_uuid(snapshot.get("channel_id")),
            "projection_message_id": parse_uuid(
                snapshot.get("channel_projection_message_id")
            ),
            "trigger_message_id": parse_uuid(snapshot.get("trigger_message_id")),
            "thread_root_message_id": parse_uuid(
                snapshot.get("thread_root_message_id")
            ),
            "agent_identity_id": parse_uuid(snapshot.get("agent_identity_id")),
            "queue_item_id": parse_uuid(snapshot.get("queue_item_id")),
        }

    def _sync_execution_placeholder_to_server_channel(
        self,
        db: Session,
        *,
        db_session: Any,
        db_run: Any | None,
        callback: AgentCallbackRequest,
    ) -> bool:
        projection_context = self._resolve_server_channel_projection_context(
            db_session=db_session,
            db_run=db_run,
        )
        channel_id = projection_context["channel_id"]
        if channel_id is None:
            return False

        full_text = self._build_full_visible_text_from_callback(callback)
        should_require_open_placeholder = not (
            callback.status == CallbackStatus.COMPLETED and full_text
        )

        placeholder = ServerChannelMessageRepository.find_execution_placeholder(
            db,
            channel_id=channel_id,
            session_id=db_session.id,
            projection_message_id=projection_context["projection_message_id"],
            run_id=db_run.id if db_run is not None else None,
            queue_item_id=projection_context["queue_item_id"],
            trigger_message_id=projection_context["trigger_message_id"],
            thread_root_message_id=projection_context["thread_root_message_id"],
            open_only=should_require_open_placeholder,
        )
        if placeholder is None:
            return False

        content = dict(placeholder.content or {})
        state_patch = callback.state_patch
        todos = list(state_patch.todos) if state_patch is not None else []
        completed_todos = sum(
            1 for item in todos if (item.status or "").strip().lower() == "completed"
        )
        current_step = state_patch.current_step if state_patch is not None else None
        summary = self._build_execution_summary_from_callback(callback) or content.get(
            "summary"
        )

        content.update(
            {
                "run_id": str(db_run.id)
                if db_run is not None
                else content.get("run_id"),
                "queue_item_id": content.get("queue_item_id")
                or (
                    str(projection_context["queue_item_id"])
                    if projection_context["queue_item_id"]
                    else None
                ),
                "channel_projection_message_id": content.get(
                    "channel_projection_message_id"
                )
                or str(placeholder.id),
                "execution_status": callback.status.value,
                "summary": summary,
                "current_step": current_step or content.get("current_step"),
                "todo_progress": {
                    "completed": completed_todos,
                    "total": len(todos),
                },
            }
        )
        if callback.status == CallbackStatus.COMPLETED:
            content["summary"] = summary or "Execution completed."
        elif callback.status == CallbackStatus.FAILED:
            content["summary"] = summary or "Execution failed."

        existing_final_text = ""
        if content.get("source") == "agent_session":
            existing_text = content.get("text")
            if isinstance(existing_text, str):
                existing_final_text = existing_text.strip()

        replacement_text = full_text or existing_final_text
        if callback.status == CallbackStatus.COMPLETED and replacement_text:
            agent_label = str(
                content.get("actor_label") or content.get("agent_label") or "Agent"
            )
            placeholder.text_preview = replacement_text
            placeholder.content = {
                "text": replacement_text,
                "actor_label": agent_label,
                "source": "agent_session",
                "session_id": str(db_session.id),
                "run_id": content.get("run_id"),
                "queue_item_id": content.get("queue_item_id"),
                "channel_projection_message_id": content.get(
                    "channel_projection_message_id"
                ),
                "execution_status": callback.status.value,
                "agent_handle": content.get("agent_handle"),
                "agent_visual_key": content.get("agent_visual_key"),
                "trigger_message_id": content.get("trigger_message_id"),
            }
            return True

        placeholder.content = content
        placeholder.text_preview = str(content.get("summary") or "").strip() or None
        return False

    def _mirror_assistant_message_to_server_channel(
        self,
        db: Session,
        *,
        db_session: Any,
        db_run: Any | None,
        db_message: Any,
    ) -> None:
        if db_message.role != "assistant":
            return

        text = _extract_visible_message_text(db_message.content) or ""
        if not text:
            text = (db_message.text_preview or "").strip()
        if not text:
            return

        projection_context = self._resolve_server_channel_projection_context(
            db_session=db_session,
            db_run=db_run,
        )
        channel_id = projection_context["channel_id"]
        if channel_id is None:
            return
        trigger_message_id = projection_context["trigger_message_id"]
        thread_root_message_id = projection_context["thread_root_message_id"]

        actor_label = "Agent"
        agent_handle = None
        agent_visual_key = None
        agent_identity_id = None
        agent_identity_raw = projection_context["agent_identity_id"]
        if agent_identity_raw:
            agent = AgentIdentityRepository.get_by_id(db, agent_identity_raw)
            if agent is not None:
                agent_identity_id = str(agent.id)
                actor_label = (
                    (agent.display_name or "").strip()
                    or (agent.handle or "").strip()
                    or actor_label
                )
                agent_handle = (agent.handle or "").strip() or None
                agent_visual_key = (agent.visual_key or "").strip() or None

        existing_projection = (
            ServerChannelMessageRepository.find_session_projection_by_run(
                db,
                channel_id=channel_id,
                session_id=db_session.id,
                projection_message_id=projection_context["projection_message_id"],
                run_id=db_run.id if db_run is not None else None,
                queue_item_id=projection_context["queue_item_id"],
            )
        )
        if existing_projection is not None:
            existing_projection.text_preview = text
            existing_content = dict(existing_projection.content or {})
            existing_projection.content = {
                "text": text,
                "actor_label": actor_label,
                "source": "agent_session",
                "session_id": str(db_session.id),
                "run_id": str(db_run.id) if db_run is not None else None,
                "queue_item_id": existing_content.get("queue_item_id"),
                "channel_projection_message_id": existing_content.get(
                    "channel_projection_message_id"
                ),
                "agent_message_id": db_message.id,
                "agent_identity_id": agent_identity_id,
                "agent_handle": agent_handle,
                "agent_visual_key": agent_visual_key,
                "trigger_message_id": str(trigger_message_id)
                if trigger_message_id
                else None,
            }
            db.flush()
            return

        ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel_id,
                author_user_id=None,
                message_type="system",
                text_preview=text,
                content={
                    "text": text,
                    "actor_label": actor_label,
                    "source": "agent_session",
                    "session_id": str(db_session.id),
                    "run_id": str(db_run.id) if db_run is not None else None,
                    "queue_item_id": str(projection_context["queue_item_id"])
                    if projection_context["queue_item_id"]
                    else None,
                    "channel_projection_message_id": str(
                        projection_context["projection_message_id"]
                    )
                    if projection_context["projection_message_id"]
                    else None,
                    "agent_message_id": db_message.id,
                    "agent_identity_id": agent_identity_id,
                    "agent_handle": agent_handle,
                    "agent_visual_key": agent_visual_key,
                    "trigger_message_id": str(trigger_message_id)
                    if trigger_message_id
                    else None,
                },
                thread_root_message_id=thread_root_message_id,
            ),
        )
        db.flush()

    def _should_skip_duplicate_result_message(
        self,
        db: Session,
        session_id: uuid.UUID,
        message: dict[str, Any],
    ) -> bool:
        message_type = str(message.get("_type", "")).strip()
        if "ResultMessage" not in message_type:
            return False
        if message.get("structured_output") is not None:
            return False

        current_text = _normalize_visible_message_text(
            _extract_visible_message_text(message)
        )
        if not current_text:
            return False

        latest_message = MessageRepository.get_latest_by_session(db, session_id)
        if latest_message is None or latest_message.role != "assistant":
            return False

        latest_text = _normalize_visible_message_text(
            _extract_visible_message_text(latest_message.content)
        )
        if not latest_text or latest_text != current_text:
            return False

        latest_type = str(latest_message.content.get("_type", "")).strip()
        return "AssistantMessage" in latest_type or "ResultMessage" in latest_type

    def _persist_message_and_tools(
        self,
        db: Session,
        session_id: uuid.UUID,
        run_id: uuid.UUID | None,
        message: dict[str, Any],
    ) -> AgentMessage:
        role = self._extract_role_from_message(message)
        text_preview = _extract_visible_message_text(message)

        db_message = MessageRepository.create(
            session_db=db,
            session_id=session_id,
            role=role,
            content=message,
            text_preview=text_preview,
        )
        db.flush()
        self._extract_tool_executions(db, message, session_id, run_id, db_message.id)
        return db_message

    def process_agent_callback(
        self, db: Session, callback: AgentCallbackRequest
    ) -> CallbackResponse:
        parsed_run_id = self._parse_run_id(callback.run_id)
        db_session, db_run = self._resolve_session_and_run(db, callback, parsed_run_id)

        if db_session is None:
            logger.warning(
                "callback_session_not_found",
                extra={
                    "callback_session_id": callback.session_id,
                    "run_id": callback.run_id,
                },
            )
            return CallbackResponse(
                session_id=callback.session_id,
                status="callback_received",
                message="Session not found yet",
            )

        if db_session.status in {"canceling", "canceled"}:
            return CallbackResponse(
                session_id=str(db_session.id),
                status=db_session.status,
                callback_status=callback.status,
            )

        derived_sdk_session_id = callback.sdk_session_id
        if (
            not derived_sdk_session_id
            and callback.new_message
            and isinstance(callback.new_message, dict)
        ):
            derived_sdk_session_id = self._extract_sdk_session_id_from_message(
                callback.new_message
            )

        if (
            derived_sdk_session_id
            and derived_sdk_session_id != db_session.sdk_session_id
        ):
            db_session.sdk_session_id = derived_sdk_session_id

        persisted_message = None
        if callback.new_message and isinstance(callback.new_message, dict):
            if self._should_skip_duplicate_result_message(
                db, db_session.id, callback.new_message
            ):
                logger.info(
                    "skip_duplicate_result_message",
                    extra={
                        "session_id": str(db_session.id),
                        "run_id": str(db_run.id) if db_run is not None else None,
                    },
                )
            else:
                persisted_message = self._persist_message_and_tools(
                    db,
                    db_session.id,
                    db_run.id if db_run is not None else None,
                    callback.new_message,
                )
            self._extract_and_persist_usage(
                db,
                db_session,
                db_run,
                callback.new_message,
            )

        if callback.state_patch is not None:
            state_patch_payload = callback.state_patch.model_dump(mode="json")
            db_session.state_patch = state_patch_payload
            if db_run is not None:
                db_run.state_patch = state_patch_payload
        placeholder_replaced_with_final_message = False
        if callback.status in {
            CallbackStatus.RUNNING,
            CallbackStatus.COMPLETED,
            CallbackStatus.FAILED,
        }:
            placeholder_replaced_with_final_message = (
                self._sync_execution_placeholder_to_server_channel(
                    db,
                    db_session=db_session,
                    db_run=db_run,
                    callback=callback,
                )
            )
        should_apply_workspace_export = self._should_apply_workspace_export(
            db,
            db_session,
            db_run,
            callback,
        )
        preserve_existing_ready_workspace = (
            should_apply_workspace_export
            and self._should_preserve_existing_ready_workspace(db_session, callback)
        )
        if preserve_existing_ready_workspace:
            logger.info(
                "preserve_existing_ready_workspace_export",
                extra={
                    "session_id": str(db_session.id),
                    "run_id": str(db_run.id) if db_run is not None else None,
                    "workspace_export_status": callback.workspace_export_status,
                },
            )
        elif should_apply_workspace_export:
            if callback.workspace_files_prefix is not None:
                db_session.workspace_files_prefix = callback.workspace_files_prefix
                if db_run is not None:
                    db_run.workspace_files_prefix = callback.workspace_files_prefix
            if callback.workspace_manifest_key is not None:
                db_session.workspace_manifest_key = callback.workspace_manifest_key
                if db_run is not None:
                    db_run.workspace_manifest_key = callback.workspace_manifest_key
            if callback.workspace_archive_key is not None:
                db_session.workspace_archive_key = callback.workspace_archive_key
                if db_run is not None:
                    db_run.workspace_archive_key = callback.workspace_archive_key
            if callback.workspace_export_status is not None:
                db_session.workspace_export_status = callback.workspace_export_status
                if db_run is not None:
                    db_run.workspace_export_status = callback.workspace_export_status
        elif db_run is not None:
            if callback.workspace_files_prefix is not None:
                db_run.workspace_files_prefix = callback.workspace_files_prefix
            if callback.workspace_manifest_key is not None:
                db_run.workspace_manifest_key = callback.workspace_manifest_key
            if callback.workspace_archive_key is not None:
                db_run.workspace_archive_key = callback.workspace_archive_key
            if callback.workspace_export_status is not None:
                db_run.workspace_export_status = callback.workspace_export_status

        if callback.workspace_archive_key is not None and db_run is not None:
            db_run.workspace_archive_key = callback.workspace_archive_key
        if callback.workspace_export_status is not None and db_run is not None:
            db_run.workspace_export_status = callback.workspace_export_status
        if callback.workspace_files_prefix is not None and db_run is not None:
            db_run.workspace_files_prefix = callback.workspace_files_prefix
        if callback.workspace_manifest_key is not None and db_run is not None:
            db_run.workspace_manifest_key = callback.workspace_manifest_key

        if db_run is not None:
            db_run.progress = int(callback.progress or 0)
            if callback.status == CallbackStatus.RUNNING:
                run_lifecycle_service.mark_running(db, db_run)
            elif callback.status == CallbackStatus.COMPLETED:
                db_run.progress = 100
                run_lifecycle_service.finalize_terminal(
                    db,
                    db_run,
                    status=callback.status.value,
                )
            elif callback.status == CallbackStatus.FAILED:
                run_lifecycle_service.finalize_terminal(
                    db,
                    db_run,
                    status=callback.status.value,
                    error_message=callback.error_message,
                )
        elif callback.status in {CallbackStatus.COMPLETED, CallbackStatus.FAILED}:
            unfinished_run = RunRepository.get_unfinished_by_session(db, db_session.id)
            if unfinished_run is None:
                db_session.status = callback.status.value

        if callback.status == CallbackStatus.COMPLETED:
            blocking_run = RunRepository.get_blocking_by_session(db, db_session.id)
            if blocking_run is None and session_queue_service.has_active_items(
                db, db_session.id
            ):
                promoted_run = session_queue_service.promote_next_if_available(
                    db, db_session
                )
                if promoted_run is not None:
                    db_session.status = "pending"

        message_to_mirror = persisted_message
        if (
            callback.status == CallbackStatus.COMPLETED
            and not placeholder_replaced_with_final_message
        ):
            if message_to_mirror is None:
                message_to_mirror = self._latest_channel_projectable_assistant_message(
                    db,
                    db_session.id,
                )
            elif isinstance(message_to_mirror.content, dict) and (
                "ResultMessage" in str(message_to_mirror.content.get("_type", ""))
            ):
                message_to_mirror = self._latest_channel_projectable_assistant_message(
                    db,
                    db_session.id,
                )

        if (
            message_to_mirror is not None
            and callback.status == CallbackStatus.COMPLETED
            and not placeholder_replaced_with_final_message
        ):
            try:
                self._mirror_assistant_message_to_server_channel(
                    db,
                    db_session=db_session,
                    db_run=db_run,
                    db_message=message_to_mirror,
                )
            except Exception:
                logger.exception(
                    "server_channel_message_mirror_failed",
                    extra={
                        "session_id": str(db_session.id),
                        "run_id": str(db_run.id) if db_run is not None else None,
                        "message_id": getattr(message_to_mirror, "id", None),
                    },
                )
            if persisted_message is not None and isinstance(callback.new_message, dict):
                try:
                    self._im_events.enqueue_assistant_message_created(
                        db,
                        db_session=db_session,
                        db_run=db_run,
                        db_message=persisted_message,
                        raw_message=callback.new_message,
                        callback=callback,
                    )
                except Exception:
                    logger.exception(
                        "im_event_enqueue_failed",
                        extra={
                            "event_type": "assistant_message.created",
                            "session_id": str(db_session.id),
                            "run_id": str(db_run.id) if db_run is not None else None,
                            "message_id": persisted_message.id,
                        },
                    )

        if callback.status in {CallbackStatus.COMPLETED, CallbackStatus.FAILED}:
            try:
                self._im_events.enqueue_run_terminal(
                    db,
                    db_session=db_session,
                    db_run=db_run,
                    callback=callback,
                )
            except Exception:
                logger.exception(
                    "im_event_enqueue_failed",
                    extra={
                        "event_type": "run.terminal",
                        "session_id": str(db_session.id),
                        "run_id": str(db_run.id) if db_run is not None else None,
                    },
                )
            pending_skill_creation_service.detect_and_create_pending(
                db,
                session=db_session,
            )
        elif (
            should_apply_workspace_export
            and not preserve_existing_ready_workspace
            and callback.workspace_export_status is not None
            and callback.workspace_export_status.strip().lower() == "ready"
            and (db_session.status or "").strip().lower() in {"completed", "failed"}
        ):
            # Workspace export may arrive in a separate callback after the initial
            # COMPLETED callback.  Trigger detection when the export becomes ready for
            # a session that is already terminal.
            pending_skill_creation_service.detect_and_create_pending(
                db,
                session=db_session,
            )

        self._assignment_service.sync_callback_status(
            db,
            session_id=db_session.id,
            callback_status=callback.status.value,
            error_message=callback.error_message,
        )
        self._sync_agent_runtime(db, db_session, callback.status.value)

        if (
            should_apply_workspace_export
            and not preserve_existing_ready_workspace
            and (db_session.workspace_export_status or "").strip().lower() == "ready"
        ):
            self._channel_artifact_service.sync_session_workspace_artifacts(
                db,
                db_session,
            )

        db.commit()
        return CallbackResponse(
            session_id=str(db_session.id),
            status=db_session.status,
            callback_status=callback.status,
        )

    def _sync_agent_runtime(
        self,
        db: Session,
        db_session: AgentSession,
        callback_status: str,
    ) -> None:
        config_snapshot = db_session.config_snapshot or {}
        if not isinstance(config_snapshot, dict):
            return
        agent_identity_id = config_snapshot.get("agent_identity_id")
        runtime_mode = (config_snapshot.get("agent_runtime_mode") or "").strip().lower()
        if not agent_identity_id or runtime_mode != "persistent":
            return
        normalized = (callback_status or "").strip().lower()
        if normalized not in {"completed", "failed", "cancelled", "canceled"}:
            return
        self._persistent_runtime_service.release_runtime_for_session(
            db,
            session_id=db_session.id,
            callback_status=normalized,
        )


def _extract_visible_message_text(message: dict[str, Any]) -> str | None:
    content = message.get("content", [])
    if isinstance(content, list):
        text_blocks: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if "TextBlock" not in str(block.get("_type", "")):
                continue
            block_text = block.get("text")
            if isinstance(block_text, str) and block_text.strip():
                text_blocks.append(block_text.strip())
        if text_blocks:
            return "\n\n".join(text_blocks)

    result = message.get("result")
    if isinstance(result, str) and result.strip():
        return result.strip()

    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def _normalize_visible_message_text(text: str | None) -> str:
    if not text:
        return ""
    return text.replace("\ufffd", "").strip()
