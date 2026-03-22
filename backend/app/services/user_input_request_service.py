import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.models.user_input_request import UserInputRequest
from app.repositories.session_repository import SessionRepository
from app.repositories.user_input_request_repository import UserInputRequestRepository
from app.schemas.user_input_request import (
    UserInputAnswerRequest,
    UserInputRequestCreateRequest,
    UserInputRequestResponse,
)

DEFAULT_EXPIRES_SECONDS = 60


class UserInputRequestService:
    @staticmethod
    def _enqueue_created_event(
        db: Session,
        *,
        db_session: AgentSession,
        request: UserInputRequest,
    ) -> None:
        from app.services.im import ImEventService

        ImEventService().enqueue_user_input_request_created(
            db,
            db_session=db_session,
            request=request,
        )

    def create_request(
        self, db: Session, request: UserInputRequestCreateRequest
    ) -> UserInputRequestResponse:
        session_id = request.session_id
        db_session = SessionRepository.get_by_id(db, session_id)
        if not db_session:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        expires_at = request.expires_at or (
            datetime.now(timezone.utc) + timedelta(seconds=DEFAULT_EXPIRES_SECONDS)
        )

        entry = UserInputRequest(
            session_id=request.session_id,
            tool_name=request.tool_name,
            tool_input=request.tool_input,
            status="pending",
            expires_at=expires_at,
        )
        UserInputRequestRepository.create(db, entry)
        db.flush()
        self._enqueue_created_event(db, db_session=db_session, request=entry)
        db.commit()
        db.refresh(entry)
        return UserInputRequestResponse.model_validate(entry)

    def get_request(
        self, db: Session, request_id: str, *, allow_expire: bool = True
    ) -> UserInputRequestResponse:
        entry = UserInputRequestRepository.get_by_id(db, request_id)
        if not entry:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"User input request not found: {request_id}",
            )

        if allow_expire and entry.status == "pending":
            now = datetime.now(timezone.utc)
            if entry.expires_at and entry.expires_at <= now:
                entry.status = "expired"
                db.commit()
                db.refresh(entry)

        return UserInputRequestResponse.model_validate(entry)

    def list_pending_for_user(
        self, db: Session, user_id: str, session_id: uuid.UUID | None = None
    ) -> list[UserInputRequestResponse]:
        entries = UserInputRequestRepository.list_pending_by_user(
            db, user_id=user_id, session_id=session_id
        )
        return [UserInputRequestResponse.model_validate(e) for e in entries]

    def answer_request(
        self,
        db: Session,
        user_id: str,
        request_id: str,
        answer_request: UserInputAnswerRequest,
    ) -> UserInputRequestResponse:
        entry = UserInputRequestRepository.get_by_id(db, request_id)
        if not entry:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"User input request not found: {request_id}",
            )

        db_session = SessionRepository.get_by_id(db, entry.session_id)
        if not db_session or db_session.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Session does not belong to the user",
            )

        if entry.status != "pending":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Request is not pending: {entry.status}",
            )

        now = datetime.now(timezone.utc)
        if entry.expires_at and entry.expires_at <= now:
            entry.status = "expired"
            db.commit()
            db.refresh(entry)
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Request expired",
            )

        entry.answers = answer_request.answers
        entry.status = "answered"
        entry.answered_at = now
        db.commit()
        db.refresh(entry)
        return UserInputRequestResponse.model_validate(entry)
