import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.repositories.message_repository import MessageRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.schemas.callback import (
    AgentCallbackRequest,
    CallbackResponse,
    CallbackStatus,
)
from app.services.run_lifecycle_service import RunLifecycleService
from app.services.session_queue_service import SessionQueueService
from app.services.session_service import SessionService
from app.utils.usage import normalize_usage_payload

logger = logging.getLogger(__name__)

run_lifecycle_service = RunLifecycleService()
session_queue_service = SessionQueueService()
session_service = SessionService()


class CallbackService:
    """Service layer for processing executor callbacks."""

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
                    continue

                ToolExecutionRepository.create(
                    session_db=session_db,
                    session_id=session_id,
                    message_id=message_id,
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

        total_cost_usd = message.get("total_cost_usd")
        duration_ms = message.get("duration_ms")
        normalized_usage = normalize_usage_payload(usage_data)

        UsageLogRepository.create(
            session_db=db,
            session_id=db_session.id,
            run_id=db_run.id if db_run else None,
            total_cost_usd=total_cost_usd,
            duration_ms=duration_ms,
            input_tokens=normalized_usage["input_tokens"],
            output_tokens=normalized_usage["output_tokens"],
            cache_creation_input_tokens=normalized_usage["cache_creation_input_tokens"],
            cache_read_input_tokens=normalized_usage["cache_read_input_tokens"],
            total_tokens=normalized_usage["total_tokens"],
            include_in_user_analytics=True,
            usage_json=usage_data,
        )

    def _persist_message_and_tools(
        self, db: Session, session_id: uuid.UUID, message: dict[str, Any]
    ) -> None:
        role = self._extract_role_from_message(message)

        text_preview = None
        content = message.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "TextBlock" in block.get("_type", ""):
                    text_preview = block.get("text", "")[:500]
                    break

        db_message = MessageRepository.create(
            session_db=db,
            session_id=session_id,
            role=role,
            content=message,
            text_preview=text_preview,
        )
        db.flush()
        self._extract_tool_executions(db, message, session_id, db_message.id)

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

        if db_session.status == "canceled":
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

        if callback.new_message and isinstance(callback.new_message, dict):
            self._persist_message_and_tools(db, db_session.id, callback.new_message)
            self._extract_and_persist_usage(
                db,
                db_session,
                db_run,
                callback.new_message,
            )

        if callback.state_patch is not None:
            db_session.state_patch = callback.state_patch.model_dump(mode="json")
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
            if callback.workspace_manifest_key is not None:
                db_session.workspace_manifest_key = callback.workspace_manifest_key
            if callback.workspace_archive_key is not None:
                db_session.workspace_archive_key = callback.workspace_archive_key
            if callback.workspace_export_status is not None:
                db_session.workspace_export_status = callback.workspace_export_status

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

        db.commit()
        return CallbackResponse(
            session_id=str(db_session.id),
            status=db_session.status,
            callback_status=callback.status,
        )
