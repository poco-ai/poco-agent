import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.session_share import (
    SessionShareCreateRequest,
    SessionShareForkResponse,
    SessionShareResponse,
    SessionShareSnapshotResponse,
    SessionShareToChannelRequest,
    SessionShareToChannelResponse,
)
from app.services.session_share_service import SessionShareService

router = APIRouter(prefix="/session-shares", tags=["session-shares"])

service = SessionShareService()


@router.post(
    "/sessions/{session_id}",
    response_model=ResponseSchema[SessionShareResponse],
)
async def create_session_share(
    session_id: uuid.UUID,
    request: SessionShareCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    share = service.create_share(
        db,
        session_id=session_id,
        owner_user_id=user_id,
        request=request,
    )
    return Response.success(
        data=SessionShareResponse.model_validate(share),
        message="Session share created successfully",
    )


@router.get(
    "/{token}",
    response_model=ResponseSchema[SessionShareSnapshotResponse],
)
async def get_session_share(
    token: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    snapshot = service.get_snapshot(db, token=token)
    return Response.success(
        data=snapshot,
        message="Session share retrieved successfully",
    )


@router.post(
    "/{token}/fork",
    response_model=ResponseSchema[SessionShareForkResponse],
)
async def fork_session_share(
    token: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.fork_share(db, token=token, target_user_id=user_id)
    return Response.success(
        data=result,
        message="Session share forked successfully",
    )


@router.post(
    "/{token}/channels",
    response_model=ResponseSchema[SessionShareToChannelResponse],
)
async def share_session_to_channel(
    token: str,
    request: SessionShareToChannelRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.share_to_channel(
        db,
        token=token,
        current_user_id=user_id,
        request=request,
    )
    return Response.success(
        data=result,
        message="Session share imported to channel successfully",
    )
