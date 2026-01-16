import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.message_repository import MessageRepository
from app.repositories.run_repository import RunRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.run import (
    RunClaimRequest,
    RunClaimResponse,
    RunFailRequest,
    RunResponse,
    RunStartRequest,
)


class RunService:
    """Service layer for run queue operations."""

    def _extract_prompt_from_message(self, message_content: object) -> str | None:
        if not isinstance(message_content, dict):
            return None

        content_blocks = message_content.get("content")
        if not isinstance(content_blocks, list):
            return None

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if "TextBlock" in str(block.get("_type", "")) and isinstance(
                block.get("text"), str
            ):
                return block["text"]
        return None

    def get_run(self, db: Session, run_id: uuid.UUID) -> RunResponse:
        db_run = RunRepository.get_by_id(db, run_id)
        if not db_run:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Run not found: {run_id}",
            )
        return RunResponse.model_validate(db_run)

    def list_runs(
        self,
        db: Session,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RunResponse]:
        runs = RunRepository.list_by_session(db, session_id, limit=limit, offset=offset)
        return [RunResponse.model_validate(r) for r in runs]

    def claim_next_run(
        self, db: Session, request: RunClaimRequest
    ) -> RunClaimResponse | None:
        worker_id = request.worker_id.strip()
        if not worker_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="worker_id cannot be empty",
            )

        schedule_modes = (
            [
                m.strip()
                for m in request.schedule_modes
                if isinstance(m, str) and m.strip()
            ]
            if request.schedule_modes
            else None
        )

        db_run = RunRepository.claim_next(
            session_db=db,
            worker_id=worker_id,
            lease_seconds=request.lease_seconds,
            schedule_modes=schedule_modes,
        )

        if not db_run:
            db.commit()
            return None

        db_session = SessionRepository.get_by_id(db, db_run.session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {db_run.session_id}",
            )

        db_message = MessageRepository.get_by_id(db, db_run.user_message_id)
        if not db_message:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Message not found: {db_run.user_message_id}",
            )

        prompt = (
            self._extract_prompt_from_message(db_message.content)
            or db_message.text_preview
        )

        if not prompt:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Unable to extract prompt from message",
            )

        db.commit()
        db.refresh(db_run)

        return RunClaimResponse(
            run=RunResponse.model_validate(db_run),
            user_id=db_session.user_id,
            prompt=prompt,
            config_snapshot=db_run.config_snapshot or db_session.config_snapshot,
            sdk_session_id=db_session.sdk_session_id,
        )

    def start_run(
        self, db: Session, run_id: uuid.UUID, request: RunStartRequest
    ) -> RunResponse:
        worker_id = request.worker_id.strip()
        if not worker_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="worker_id cannot be empty",
            )

        db_run = RunRepository.get_by_id(db, run_id)
        if not db_run:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Run not found: {run_id}",
            )

        if db_run.status in ["completed", "failed", "canceled"]:
            return RunResponse.model_validate(db_run)

        if db_run.status == "running":
            if db_run.claimed_by and db_run.claimed_by != worker_id:
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Run is claimed by another worker",
                )
            return RunResponse.model_validate(db_run)

        if db_run.status not in ["claimed", "queued"]:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Run status cannot be started: {db_run.status}",
            )

        if db_run.claimed_by and db_run.claimed_by != worker_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Run is claimed by another worker",
            )

        now = datetime.now(timezone.utc)
        db_run.status = "running"
        db_run.started_at = now
        db_run.lease_expires_at = None
        db_run.attempts += 1

        db_session = SessionRepository.get_by_id(db, db_run.session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {db_run.session_id}",
            )
        db_session.status = "running"

        db.commit()
        db.refresh(db_run)

        return RunResponse.model_validate(db_run)

    def fail_run(
        self,
        db: Session,
        run_id: uuid.UUID,
        request: RunFailRequest,
    ) -> RunResponse:
        worker_id = request.worker_id.strip()
        if not worker_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="worker_id cannot be empty",
            )

        db_run = RunRepository.get_by_id(db, run_id)
        if not db_run:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Run not found: {run_id}",
            )

        if db_run.claimed_by and db_run.claimed_by != worker_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Run is claimed by another worker",
            )

        now = datetime.now(timezone.utc)
        db_run.status = "failed"
        db_run.last_error = request.error_message
        db_run.finished_at = now
        db_run.lease_expires_at = None

        db_session = SessionRepository.get_by_id(db, db_run.session_id)
        if db_session:
            db_session.status = "failed"

        db.commit()
        db.refresh(db_run)

        return RunResponse.model_validate(db_run)
