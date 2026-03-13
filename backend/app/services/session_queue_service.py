import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_message import AgentMessage
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.session_queue_item import AgentSessionQueueItem
from app.repositories.message_repository import MessageRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_queue_item_repository import SessionQueueItemRepository
from app.schemas.session_queue_item import (
    SessionQueueItemResponse,
    SessionQueueItemUpdateRequest,
)
from app.schemas.task import TaskEnqueueResponse


class SessionQueueService:
    @staticmethod
    def _normalize_prompt(prompt: str) -> str:
        value = (prompt or "").strip()
        if not value:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Prompt cannot be empty",
            )
        return value

    @staticmethod
    def extract_session_config(
        run_config_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(run_config_snapshot, dict):
            return None
        session_config = dict(run_config_snapshot)
        session_config.pop("input_files", None)
        return session_config or None

    @staticmethod
    def clear_execution_state(db_session: AgentSession) -> None:
        db_session.state_patch = {}
        db_session.workspace_archive_url = None
        db_session.workspace_files_prefix = None
        db_session.workspace_manifest_key = None
        db_session.workspace_archive_key = None
        db_session.workspace_export_status = None

    @staticmethod
    def _move_item_to_front(
        db: Session,
        *,
        session_id: uuid.UUID,
        item: AgentSessionQueueItem,
        active_items: list[AgentSessionQueueItem],
    ) -> None:
        if active_items and active_items[0].id == item.id:
            return

        min_sequence_no = SessionQueueItemRepository.get_min_sequence_no(
            db,
            session_id,
        )
        item.sequence_no = 1 if min_sequence_no is None else min_sequence_no - 1

    def _promote_item(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        item: AgentSessionQueueItem,
    ) -> AgentRun:
        run_snapshot = (
            dict(item.run_config_snapshot)
            if isinstance(item.run_config_snapshot, dict)
            else None
        )
        db_message, db_run = self.materialize_run(
            db,
            db_session=db_session,
            prompt=item.prompt,
            permission_mode=item.permission_mode,
            schedule_mode="immediate",
            run_config_snapshot=run_snapshot,
        )
        item.status = "promoted"
        item.linked_run_id = db_run.id
        item.linked_user_message_id = db_message.id
        db.flush()
        return db_run

    def list_items(
        self, db: Session, session_id: uuid.UUID
    ) -> list[AgentSessionQueueItem]:
        return SessionQueueItemRepository.list_active_by_session(db, session_id)

    def list_item_responses(
        self, db: Session, session_id: uuid.UUID
    ) -> list[SessionQueueItemResponse]:
        return [
            SessionQueueItemResponse.model_validate(item)
            for item in self.list_items(db, session_id)
        ]

    def count_active_items(self, db: Session, session_id: uuid.UUID) -> int:
        return SessionQueueItemRepository.count_active_by_session(db, session_id)

    def has_active_items(self, db: Session, session_id: uuid.UUID) -> bool:
        return SessionQueueItemRepository.has_active_items(db, session_id)

    def get_effective_base_config(
        self, db: Session, db_session: AgentSession
    ) -> dict[str, Any] | None:
        last_item = SessionQueueItemRepository.get_last_active_item(db, db_session.id)
        if last_item and isinstance(last_item.run_config_snapshot, dict):
            return self.extract_session_config(last_item.run_config_snapshot)
        return dict(db_session.config_snapshot or {}) or None

    def get_existing_enqueue_response(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        client_request_id: str | None,
    ) -> TaskEnqueueResponse | None:
        normalized_id = (client_request_id or "").strip()
        if not normalized_id:
            return None
        item = SessionQueueItemRepository.get_by_client_request_id(
            db,
            session_id=session_id,
            client_request_id=normalized_id,
        )
        if not item:
            return None

        queued_query_count = self.count_active_items(db, session_id)
        if item.status in {"queued", "paused"}:
            return TaskEnqueueResponse(
                session_id=session_id,
                accepted_type="queued_query",
                queue_item_id=item.id,
                status=item.status,
                queued_query_count=queued_query_count,
            )
        if item.status == "promoted" and item.linked_run_id:
            run = RunRepository.get_by_id(db, item.linked_run_id)
            return TaskEnqueueResponse(
                session_id=session_id,
                accepted_type="run",
                run_id=item.linked_run_id,
                status=run.status if run else "queued",
                queued_query_count=queued_query_count,
            )
        return None

    def enqueue(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        prompt: str,
        permission_mode: str,
        run_config_snapshot: dict[str, Any] | None,
        client_request_id: str | None = None,
    ) -> AgentSessionQueueItem:
        sequence_no = (
            SessionQueueItemRepository.get_max_sequence_no(db, db_session.id) + 1
        )
        normalized_request_id = (client_request_id or "").strip() or None
        item = SessionQueueItemRepository.create(
            db,
            session_id=db_session.id,
            sequence_no=sequence_no,
            prompt=self._normalize_prompt(prompt),
            permission_mode=permission_mode,
            run_config_snapshot=run_config_snapshot,
            client_request_id=normalized_request_id,
        )
        db.flush()
        return item

    def materialize_run(
        self,
        db: Session,
        *,
        db_session: AgentSession,
        prompt: str,
        permission_mode: str,
        schedule_mode: str,
        run_config_snapshot: dict[str, Any] | None,
        scheduled_at: datetime | None = None,
    ) -> tuple[AgentMessage, AgentRun]:
        normalized_prompt = self._normalize_prompt(prompt)
        if schedule_mode == "immediate":
            self.clear_execution_state(db_session)
        db_session.config_snapshot = self.extract_session_config(run_config_snapshot)

        user_message_content = {
            "_type": "UserMessage",
            "content": [{"_type": "TextBlock", "text": normalized_prompt}],
        }
        db_message = MessageRepository.create(
            session_db=db,
            session_id=db_session.id,
            role="user",
            content=user_message_content,
            text_preview=normalized_prompt[:500],
        )
        db.flush()

        db_run = RunRepository.create(
            session_db=db,
            session_id=db_session.id,
            user_message_id=db_message.id,
            permission_mode=permission_mode,
            schedule_mode=schedule_mode,
            scheduled_at=scheduled_at,
            config_snapshot=run_config_snapshot or None,
        )
        db_session.status = "pending"
        db.flush()
        return db_message, db_run

    def promote_next_if_available(
        self, db: Session, db_session: AgentSession
    ) -> AgentRun | None:
        if RunRepository.get_blocking_by_session(db, db_session.id):
            return None
        item = SessionQueueItemRepository.get_head_for_update(db, db_session.id)
        if not item:
            return None
        return self._promote_item(
            db,
            db_session=db_session,
            item=item,
        )

    def pause_active_items(self, db: Session, session_id: uuid.UUID) -> int:
        return SessionQueueItemRepository.mark_paused(db, session_id=session_id)

    def cancel_active_items(self, db: Session, session_id: uuid.UUID) -> int:
        return SessionQueueItemRepository.mark_canceled(db, session_id=session_id)

    def update_item(
        self,
        db: Session,
        db_session: AgentSession,
        item_id: uuid.UUID,
        request: SessionQueueItemUpdateRequest,
    ) -> AgentSessionQueueItem:
        item = SessionQueueItemRepository.get_by_id_for_update(db, item_id)
        if (
            not item
            or item.session_id != db_session.id
            or item.status not in {"queued", "paused"}
        ):
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Queued query not found: {item_id}",
            )

        if request.prompt is not None:
            item.prompt = self._normalize_prompt(request.prompt)

        if request.attachments is not None:
            snapshot = (
                dict(item.run_config_snapshot)
                if isinstance(item.run_config_snapshot, dict)
                else {}
            )
            if request.attachments:
                snapshot["input_files"] = [
                    attachment.model_dump(mode="json")
                    for attachment in request.attachments
                ]
            else:
                snapshot.pop("input_files", None)
            item.run_config_snapshot = snapshot or None

        db.flush()
        return item

    def cancel_item(
        self,
        db: Session,
        db_session: AgentSession,
        item_id: uuid.UUID,
    ) -> AgentSessionQueueItem:
        item = SessionQueueItemRepository.get_by_id_for_update(db, item_id)
        if (
            not item
            or item.session_id != db_session.id
            or item.status not in {"queued", "paused"}
        ):
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Queued query not found: {item_id}",
            )
        item.status = "canceled"
        db.flush()
        return item

    def send_now(
        self,
        db: Session,
        db_session: AgentSession,
        item_id: uuid.UUID,
    ) -> TaskEnqueueResponse:
        active_items = SessionQueueItemRepository.list_active_by_session(
            db,
            db_session.id,
            for_update=True,
        )
        item = next((entry for entry in active_items if entry.id == item_id), None)
        if item is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Queued query not found: {item_id}",
            )

        item.status = "queued"

        blocking_run = RunRepository.get_blocking_by_session(db, db_session.id)
        if blocking_run is not None:
            self._move_item_to_front(
                db,
                session_id=db_session.id,
                item=item,
                active_items=active_items,
            )
            db.flush()
            return TaskEnqueueResponse(
                session_id=db_session.id,
                accepted_type="queued_query",
                queue_item_id=item.id,
                status=item.status,
                queued_query_count=self.count_active_items(db, db_session.id),
            )

        promoted_run = self._promote_item(
            db,
            db_session=db_session,
            item=item,
        )
        db.flush()
        return TaskEnqueueResponse(
            session_id=db_session.id,
            accepted_type="run",
            run_id=promoted_run.id,
            status=promoted_run.status,
            queued_query_count=self.count_active_items(db, db_session.id),
        )
