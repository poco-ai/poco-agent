import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.response import Response, ResponseSchema
from app.schemas.mcp_connection import McpConnectionResponse
from app.schemas.run import (
    RunClaimRequest,
    RunClaimResponse,
    RunFailRequest,
    RunResponse,
    RunStartRequest,
)
from app.services.run_service import RunService
from app.services.mcp_connection_service import McpConnectionService
from app.services.session_service import SessionService

router = APIRouter(prefix="/runs", tags=["runs"])

run_service = RunService()
mcp_connection_service = McpConnectionService()
session_service = SessionService()


@router.post("/claim", response_model=ResponseSchema[RunClaimResponse | None])
async def claim_next_run(
    request: RunClaimRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Claim the next available run for execution."""
    result = run_service.claim_next_run(db, request)
    return Response.success(data=result, message="Run claimed" if result else "No runs")


@router.post("/{run_id}/start", response_model=ResponseSchema[RunResponse])
async def start_run(
    run_id: uuid.UUID,
    request: RunStartRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Mark a run as running (after dispatch accepted)."""
    result = run_service.start_run(db, run_id, request)
    return Response.success(data=result, message="Run started")


@router.post("/{run_id}/fail", response_model=ResponseSchema[RunResponse])
async def fail_run(
    run_id: uuid.UUID,
    request: RunFailRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Mark a run as failed."""
    result = run_service.fail_run(db, run_id, request)
    return Response.success(data=result, message="Run marked as failed")


@router.get("/{run_id}", response_model=ResponseSchema[RunResponse])
async def get_run(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get run details."""
    result = run_service.get_run(db, run_id)
    db_session = session_service.get_session(db, result.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    return Response.success(data=result, message="Run retrieved successfully")


@router.get("/session/{session_id}", response_model=ResponseSchema[list[RunResponse]])
async def list_runs_by_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List runs for a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    runs = run_service.list_runs(db, session_id, limit=limit, offset=offset)
    return Response.success(data=runs, message="Runs retrieved successfully")


@router.get(
    "/{run_id}/mcp-connections",
    response_model=ResponseSchema[list[McpConnectionResponse]],
)
async def list_run_mcp_connections(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = run_service.get_run(db, run_id)
    db_session = session_service.get_session(db, result.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    return Response.success(
        data=mcp_connection_service.list_run_connections(db, run_id),
        message="Run MCP connections retrieved successfully",
    )
