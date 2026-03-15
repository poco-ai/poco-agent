from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.user_input_request import UserInputRequest
from app.repositories.im_event_outbox_repository import ImEventOutboxRepository
from app.repositories.run_repository import RunRepository
from app.schemas.callback import AgentCallbackRequest
from app.schemas.im_event import (
    EventStateSnapshot,
    ImBackendEvent,
    MessageSnapshot,
    RunSnapshot,
    SessionSnapshot,
    UserInputRequestSnapshot,
)


class ImEventService:
    EVENT_VERSION = 1

    def enqueue_assistant_message_created(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        db_run: AgentRun | None,
        db_message: AgentMessage,
        raw_message: dict[str, Any],
        callback: AgentCallbackRequest,
    ) -> None:
        text = _extract_visible_assistant_text(raw_message)
        if not text:
            return

        event_id = uuid.uuid4()
        event = ImBackendEvent(
            id=str(event_id),
            type="assistant_message.created",
            version=self.EVENT_VERSION,
            occurred_at=callback.time,
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            run=_build_run_snapshot(
                db_run,
                callback_status=callback.status.value,
                error_message=callback.error_message,
            ),
            state=_build_state_snapshot(callback),
            message=MessageSnapshot(
                id=db_message.id,
                role="assistant",
                text=text,
                text_preview=(db_message.text_preview or text[:500] or None),
            ),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=f"assistant-message:{db_message.id}",
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=db_run.id if db_run is not None else None,
            message_id=db_message.id,
            user_input_request_id=None,
            payload=event.model_dump(mode="json"),
        )

    def enqueue_run_terminal(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        db_run: AgentRun | None,
        callback: AgentCallbackRequest,
    ) -> None:
        terminal_run = db_run
        if terminal_run is None:
            terminal_run = RunRepository.get_latest_terminal_by_session(
                db, db_session.id
            )

        event_id = uuid.uuid4()
        run_status = (
            terminal_run.status
            if terminal_run is not None and (terminal_run.status or "").strip()
            else callback.status.value
        )
        event_key = (
            f"run-terminal:{terminal_run.id}:{run_status}"
            if terminal_run is not None
            else f"run-terminal:session:{db_session.id}:{run_status}"
        )
        event = ImBackendEvent(
            id=str(event_id),
            type="run.terminal",
            version=self.EVENT_VERSION,
            occurred_at=callback.time,
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            run=_build_run_snapshot(
                terminal_run,
                callback_status=callback.status.value,
                error_message=callback.error_message,
            ),
            state=_build_state_snapshot(callback),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=event_key,
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=terminal_run.id if terminal_run is not None else None,
            message_id=None,
            user_input_request_id=None,
            payload=event.model_dump(mode="json"),
        )

    def enqueue_user_input_request_created(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        request: UserInputRequest,
    ) -> None:
        event_id = uuid.uuid4()
        event = ImBackendEvent(
            id=str(event_id),
            type="user_input_request.created",
            version=self.EVENT_VERSION,
            occurred_at=request.created_at or datetime.now(timezone.utc),
            user_id=db_session.user_id,
            session=_build_session_snapshot(db_session),
            user_input_request=UserInputRequestSnapshot(
                id=str(request.id),
                tool_name=request.tool_name,
                tool_input=request.tool_input or {},
                status=request.status,
                expires_at=request.expires_at,
                answered_at=request.answered_at,
            ),
        )
        ImEventOutboxRepository.create_if_absent(
            db,
            event_key=f"user-input-created:{request.id}",
            event_type=event.type,
            event_version=event.version,
            user_id=db_session.user_id,
            session_id=db_session.id,
            run_id=None,
            message_id=None,
            user_input_request_id=request.id,
            payload=event.model_dump(mode="json"),
        )


def _build_session_snapshot(db_session: AgentSession) -> SessionSnapshot:
    return SessionSnapshot(
        id=str(db_session.id),
        title=(db_session.title or None),
        status=db_session.status,
    )


def _build_run_snapshot(
    db_run: AgentRun | None,
    *,
    callback_status: str | None = None,
    error_message: str | None = None,
) -> RunSnapshot | None:
    if db_run is None and not callback_status:
        return None
    return RunSnapshot(
        id=str(db_run.id) if db_run is not None else None,
        status=(db_run.status if db_run is not None else callback_status),
        progress=(db_run.progress if db_run is not None else None),
        error_message=(
            db_run.last_error
            if db_run is not None and db_run.last_error
            else error_message
        ),
    )


def _build_state_snapshot(callback: AgentCallbackRequest) -> EventStateSnapshot | None:
    state_patch = callback.state_patch
    if state_patch is None:
        return None
    todos = state_patch.todos or []
    completed = sum(1 for item in todos if item.status == "completed")
    return EventStateSnapshot(
        callback_status=callback.status.value,
        current_step=state_patch.current_step,
        todos_total=len(todos),
        todos_completed=completed,
    )


def _extract_visible_assistant_text(message: dict[str, Any]) -> str:
    message_type = str(message.get("_type") or "").strip()
    if "ResultMessage" in message_type:
        result = message.get("result")
        if isinstance(result, str) and result.strip():
            return result.replace("\ufffd", "").strip()
        return ""

    if "AssistantMessage" not in message_type:
        return ""

    content = message.get("content")
    if not isinstance(content, list):
        return ""

    raw_texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("parent_tool_use_id"):
            continue
        if "TextBlock" not in str(block.get("_type") or ""):
            continue
        block_text = block.get("text")
        if isinstance(block_text, str) and block_text.strip():
            raw_texts.append(block_text.strip())

    if not raw_texts:
        return ""

    cleaned: list[str] = []
    seen: set[str] = set()
    for text in raw_texts:
        normalized = text.replace("\ufffd", "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    return "\n\n".join(cleaned)
