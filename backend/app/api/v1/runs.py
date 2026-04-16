import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.run_repository import RunRepository
from app.schemas.computer import ComputerBrowserScreenshotResponse
from app.schemas.response import Response, ResponseSchema
from app.schemas.run import (
    RunClaimRequest,
    RunClaimResponse,
    RunFailRequest,
    RunResponse,
    RunStartRequest,
)
from app.schemas.tool_execution import ToolExecutionDeltaResponse, ToolExecutionResponse
from app.schemas.workspace import FileNode, WorkspaceArchiveResponse
from app.services.run_service import RunService
from app.services.session_service import SessionService
from app.services.storage_service import S3StorageService
from app.services.tool_execution_service import ToolExecutionService
from app.services.workspace_archive_service import WorkspaceArchiveService
from app.utils.computer import build_browser_screenshot_key
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_manifest,
    extract_manifest_files,
    normalize_manifest_path,
)

router = APIRouter(prefix="/runs", tags=["runs"])

run_service = RunService()
session_service = SessionService()
tool_execution_service = ToolExecutionService()
storage_service = S3StorageService()
workspace_archive_service = WorkspaceArchiveService()


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
    "/{run_id}/tool-executions",
    response_model=ResponseSchema[list[ToolExecutionResponse]],
)
async def list_tool_executions_by_run(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = run_service.get_run(db, run_id)
    db_session = session_service.get_session(db, result.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    executions = tool_execution_service.get_tool_executions_by_run(
        db, run_id, limit=limit, offset=offset
    )
    return Response.success(
        data=[ToolExecutionResponse.model_validate(e) for e in executions],
        message="Run tool executions retrieved successfully",
    )


@router.get(
    "/{run_id}/tool-executions/delta",
    response_model=ResponseSchema[ToolExecutionDeltaResponse],
)
async def list_tool_executions_delta_by_run(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    after_created_at: datetime | None = Query(default=None),
    after_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = run_service.get_run(db, run_id)
    db_session = session_service.get_session(db, result.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    if after_id is not None and after_created_at is None:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="after_created_at is required when after_id is provided",
        )

    payload = tool_execution_service.get_tool_executions_delta_by_run(
        db,
        run_id,
        after_created_at=after_created_at,
        after_id=after_id,
        limit=limit,
    )
    return Response.success(
        data=payload,
        message="Run tool executions delta retrieved successfully",
    )


def _build_file_nodes_from_export(
    *,
    manifest_key: str | None,
    workspace_files_prefix: str | None,
) -> list[FileNode]:
    if not manifest_key:
        return []

    manifest = storage_service.get_manifest(manifest_key)
    raw_nodes = build_nodes_from_manifest(manifest)
    manifest_files = extract_manifest_files(manifest)
    prefix = (workspace_files_prefix or "").rstrip("/")
    file_url_map: dict[str, str] = {}

    for file_entry in manifest_files:
        file_path = normalize_manifest_path(file_entry.get("path"))
        if not file_path:
            continue
        object_key = (
            file_entry.get("key")
            or file_entry.get("object_key")
            or file_entry.get("oss_key")
            or file_entry.get("s3_key")
        )
        if not object_key and prefix:
            object_key = f"{prefix}/{file_path.lstrip('/')}"
        if not object_key:
            continue
        mime_type = file_entry.get("mimeType") or file_entry.get("mime_type")
        file_url_map[file_path] = storage_service.presign_get(
            object_key,
            response_content_disposition="inline",
            response_content_type=mime_type,
        )

    def build_file_url(file_path: str) -> str | None:
        normalized = normalize_manifest_path(file_path) or file_path
        return file_url_map.get(normalized)

    return build_workspace_file_nodes(raw_nodes, file_url_builder=build_file_url)


@router.get("/{run_id}/workspace/files", response_model=ResponseSchema[list[FileNode]])
async def get_run_workspace_files(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_run = RunRepository.get_by_id(db, run_id)
    if db_run is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Run not found: {run_id}",
        )
    db_session = session_service.get_session(db, db_run.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    nodes = _build_file_nodes_from_export(
        manifest_key=db_run.workspace_manifest_key,
        workspace_files_prefix=db_run.workspace_files_prefix,
    )
    return Response.success(data=nodes, message="Run workspace files retrieved")


@router.get(
    "/{run_id}/workspace/archive",
    response_model=ResponseSchema[WorkspaceArchiveResponse],
)
async def get_run_workspace_archive(
    run_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_run = RunRepository.get_by_id(db, run_id)
    if db_run is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Run not found: {run_id}",
        )
    db_session = session_service.get_session(db, db_run.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )

    filename = f"workspace-{run_id}.zip"
    archive_key = (db_run.workspace_archive_key or "").strip()
    if not archive_key or db_run.workspace_export_status != "ready":
        return Response.success(
            data=WorkspaceArchiveResponse(url=None, filename=filename),
            message="Run workspace export not ready",
        )

    url = storage_service.presign_get(
        archive_key,
        response_content_disposition=f'attachment; filename="{filename}"',
        response_content_type="application/zip",
    )
    return Response.success(
        data=WorkspaceArchiveResponse(url=url, filename=filename),
        message="Run workspace archive URL generated",
    )


@router.get(
    "/{run_id}/workspace/folder-archive",
    response_model=ResponseSchema[WorkspaceArchiveResponse],
)
async def get_run_workspace_folder_archive(
    run_id: uuid.UUID,
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_run = RunRepository.get_by_id(db, run_id)
    if db_run is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Run not found: {run_id}",
        )
    db_session = session_service.get_session(db, db_run.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )

    normalized_path = normalize_manifest_path(path)
    folder_name = (
        normalized_path.strip("/").split("/")[-1]
        if normalized_path
        else f"workspace-{run_id}"
    )
    filename = f"{folder_name or f'workspace-{run_id}'}.zip"
    if db_run.workspace_export_status != "ready":
        return Response.success(
            data=WorkspaceArchiveResponse(url=None, filename=filename),
            message="Run workspace export not ready",
        )
    archive = workspace_archive_service.get_folder_archive_for_run(
        session=db_session,
        run=db_run,
        folder_path=path,
    )
    return Response.success(
        data=archive,
        message="Run workspace folder archive URL generated",
    )


@router.get(
    "/{run_id}/computer/browser/{tool_use_id}",
    response_model=ResponseSchema[ComputerBrowserScreenshotResponse],
)
async def get_run_browser_screenshot(
    run_id: uuid.UUID,
    tool_use_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    db_run = RunRepository.get_by_id(db, run_id)
    if db_run is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Run not found: {run_id}",
        )
    db_session = session_service.get_session(db, db_run.session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Run does not belong to the user",
        )
    key = build_browser_screenshot_key(
        user_id=user_id,
        session_id=str(db_session.id),
        run_id=str(run_id),
        tool_use_id=tool_use_id,
    )
    if not storage_service.exists(key):
        legacy_key = build_browser_screenshot_key(
            user_id=user_id,
            session_id=str(db_session.id),
            tool_use_id=tool_use_id,
        )
        if storage_service.exists(legacy_key):
            key = legacy_key
        else:
            raise HTTPException(status_code=404, detail="Browser screenshot not ready")
    url = storage_service.presign_get(
        key,
        response_content_disposition="inline",
        response_content_type="image/png",
    )
    return Response.success(
        data=ComputerBrowserScreenshotResponse(tool_use_id=tool_use_id, url=url),
        message="Run browser screenshot URL generated",
    )
