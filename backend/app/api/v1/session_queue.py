import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.response import Response, ResponseSchema
from app.schemas.session_queue_item import (
    SessionQueueItemResponse,
    SessionQueueItemUpdateRequest,
)
from app.schemas.task import TaskEnqueueResponse
from app.services.session_queue_service import SessionQueueService
from app.services.session_service import SessionService

router = APIRouter(
    prefix="/sessions/{session_id}/queued-queries", tags=["session-queue"]
)

session_service = SessionService()
session_queue_service = SessionQueueService()


def _get_owned_session(db: Session, session_id: uuid.UUID, user_id: str):
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    return db_session


@router.get("", response_model=ResponseSchema[list[SessionQueueItemResponse]])
async def list_queued_queries(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = _get_owned_session(db, session_id, user_id)
    items = session_queue_service.list_item_responses(db, db_session.id)
    return Response.success(data=items, message="Queued queries retrieved successfully")


@router.patch("/{item_id}", response_model=ResponseSchema[SessionQueueItemResponse])
async def update_queued_query(
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    request: SessionQueueItemUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = _get_owned_session(db, session_id, user_id)
    item = session_queue_service.update_item(db, db_session, item_id, request)
    db.commit()
    db.refresh(item)
    return Response.success(
        data=SessionQueueItemResponse.model_validate(item),
        message="Queued query updated successfully",
    )


@router.delete("/{item_id}", response_model=ResponseSchema[SessionQueueItemResponse])
async def delete_queued_query(
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = _get_owned_session(db, session_id, user_id)
    item = session_queue_service.cancel_item(db, db_session, item_id)
    db.commit()
    db.refresh(item)
    return Response.success(
        data=SessionQueueItemResponse.model_validate(item),
        message="Queued query deleted successfully",
    )


@router.post("/{item_id}/send-now", response_model=ResponseSchema[TaskEnqueueResponse])
async def send_queued_query_now(
    session_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_session = _get_owned_session(db, session_id, user_id)
    result = session_queue_service.send_now(db, db_session, item_id)
    db.commit()
    return Response.success(data=result, message="Queued query updated successfully")
