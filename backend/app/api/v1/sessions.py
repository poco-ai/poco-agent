import uuid
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.observability.request_context import get_request_id, get_trace_id
from app.core.settings import get_settings
from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.message import (
    MessageAttachmentsResponse,
    MessageResponse,
    MessageWithFilesResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.schemas.session import (
    SessionBranchRequest,
    SessionBranchResponse,
    SessionCancelRequest,
    SessionCancelResponse,
    SessionCreateRequest,
    SessionEditMessageRequest,
    SessionRegenerateRequest,
    SessionResponse,
    SessionStateResponse,
    SessionUpdateRequest,
)
from app.schemas.task import TaskEnqueueResponse
from app.schemas.computer import ComputerBrowserScreenshotResponse
from app.schemas.tool_execution import ToolExecutionResponse
from app.schemas.usage import UsageResponse
from app.schemas.workspace import FileNode, WorkspaceArchiveResponse
from app.services.message_service import MessageService
from app.services.session_service import SessionService
from app.services.storage_service import S3StorageService
from app.services.tool_execution_service import ToolExecutionService
from app.services.usage_service import UsageService
from app.utils.computer import build_browser_screenshot_key
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_manifest,
    extract_manifest_files,
    normalize_manifest_path,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

session_service = SessionService()
message_service = MessageService()
tool_execution_service = ToolExecutionService()
usage_service = UsageService()
storage_service = S3StorageService()


def _cancel_executor_manager(session_id: uuid.UUID, reason: str | None) -> bool:
    """Best-effort cancel request to Executor Manager.

    This stops the executor container for the session, but cancellation should still
    succeed locally even if Executor Manager is unavailable.
    """
    settings = get_settings()
    url = f"{settings.executor_manager_url}/api/v1/executor/cancel"

    payload = {"session_id": str(session_id)}
    if reason is not None:
        payload["reason"] = reason

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    request_id = get_request_id()
    if request_id:
        headers["X-Request-ID"] = request_id
    trace_id = get_trace_id()
    if trace_id:
        headers["X-Trace-ID"] = trace_id

    try:
        req = Request(  # noqa: S310
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(req, timeout=3) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict):
            return parsed.get("code") == 0
    except (HTTPError, URLError, ValueError):
        return False
    except Exception:
        return False
    return False


@router.post("", response_model=ResponseSchema[SessionResponse])
async def create_session(
    request: SessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Creates a new session."""
    db_session = session_service.create_session(db, user_id, request)
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session created successfully",
    )


@router.get("", response_model=ResponseSchema[list[SessionResponse]])
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    limit: int = 100,
    offset: int = 0,
    project_id: uuid.UUID | None = Query(default=None),
    kind: str = Query(default="chat"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Lists sessions."""
    kind_filter = kind.strip().lower()
    kind_value = None if kind_filter in {"", "all"} else kind_filter
    sessions = session_service.list_sessions(
        db,
        user_id,
        limit,
        offset,
        project_id,
        kind=kind_value,
    )
    return Response.success(
        data=[SessionResponse.model_validate(s) for s in sessions],
        message="Sessions retrieved successfully",
    )


@router.get("/{session_id}", response_model=ResponseSchema[SessionResponse])
async def get_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets session details."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session retrieved successfully",
    )


@router.get("/{session_id}/state", response_model=ResponseSchema[SessionStateResponse])
async def get_session_state(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets session state details."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    return Response.success(
        data=SessionStateResponse.model_validate(db_session),
        message="Session state retrieved successfully",
    )


@router.patch("/{session_id}", response_model=ResponseSchema[SessionResponse])
async def update_session(
    session_id: uuid.UUID,
    request: SessionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Updates a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    db_session = session_service.update_session(db, session_id, request)
    return Response.success(
        data=SessionResponse.model_validate(db_session),
        message="Session updated successfully",
    )


@router.post(
    "/{session_id}/cancel", response_model=ResponseSchema[SessionCancelResponse]
)
async def cancel_session(
    session_id: uuid.UUID,
    request: SessionCancelRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Cancel a session (cancel all unfinished runs and stop executor container)."""
    db_session, canceled_runs, expired_requests = session_service.cancel_session(
        db, session_id, user_id=user_id, reason=request.reason
    )
    executor_cancelled = _cancel_executor_manager(session_id, request.reason)

    return Response.success(
        data=SessionCancelResponse(
            session_id=db_session.id,
            status=db_session.status,
            canceled_runs=canceled_runs,
            expired_user_input_requests=expired_requests,
            executor_cancelled=executor_cancelled,
        ),
        message="Session canceled successfully",
    )


@router.post(
    "/{session_id}/branch", response_model=ResponseSchema[SessionBranchResponse]
)
async def branch_session(
    session_id: uuid.UUID,
    request: SessionBranchRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Create a branched session by cloning state up to a message checkpoint."""
    branched = session_service.branch_session(
        db,
        session_id,
        user_id=user_id,
        cutoff_message_id=request.message_id,
    )
    return Response.success(
        data=SessionBranchResponse(
            session_id=branched.id,
            source_session_id=session_id,
            cutoff_message_id=request.message_id,
        ),
        message="Session branched successfully",
    )


@router.post(
    "/{session_id}/regenerate", response_model=ResponseSchema[TaskEnqueueResponse]
)
async def regenerate_message(
    session_id: uuid.UUID,
    request: SessionRegenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Regenerate from a prior turn by pruning later messages then queueing a new run."""
    result = session_service.regenerate_from_message(
        db,
        session_id,
        user_id=user_id,
        user_message_id=request.user_message_id,
        assistant_message_id=request.assistant_message_id,
    )
    return Response.success(data=result, message="Message regenerated successfully")


@router.post(
    "/{session_id}/edit-message", response_model=ResponseSchema[TaskEnqueueResponse]
)
async def edit_message_and_regenerate(
    session_id: uuid.UUID,
    request: SessionEditMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Edit a user message and regenerate by pruning all subsequent history."""
    result = session_service.edit_message_and_regenerate(
        db,
        session_id,
        user_id=user_id,
        user_message_id=request.user_message_id,
        content=request.content,
    )
    return Response.success(data=result, message="Message edited and regenerated")


@router.delete("/{session_id}", response_model=ResponseSchema[dict])
async def delete_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Soft deletes a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    session_service.delete_session(db, session_id)
    return Response.success(
        data={"id": session_id},
        message="Session deleted successfully",
    )


@router.get(
    "/{session_id}/messages", response_model=ResponseSchema[list[MessageResponse]]
)
async def get_session_messages(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets all messages for a session."""
    # Verify session exists
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    messages = message_service.get_messages(db, session_id)
    return Response.success(
        data=[MessageResponse.model_validate(m) for m in messages],
        message="Messages retrieved successfully",
    )


@router.get(
    "/{session_id}/messages-with-files",
    response_model=ResponseSchema[list[MessageWithFilesResponse]],
)
async def get_session_messages_with_files(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets all messages for a session with per-message attachments."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    messages = message_service.get_messages_with_files(db, session_id, user_id=user_id)
    return Response.success(
        data=messages,
        message="Messages retrieved successfully",
    )


@router.get(
    "/{session_id}/message-attachments",
    response_model=ResponseSchema[list[MessageAttachmentsResponse]],
)
async def get_session_message_attachments(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets per-message attachments for a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    attachments = message_service.get_message_attachments(
        db, session_id, user_id=user_id
    )
    return Response.success(
        data=attachments,
        message="Message attachments retrieved successfully",
    )


@router.get(
    "/{session_id}/tool-executions",
    response_model=ResponseSchema[list[ToolExecutionResponse]],
)
async def get_session_tool_executions(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(default=500, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets all tool executions for a session."""
    # Verify session exists
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    executions = tool_execution_service.get_tool_executions(
        db,
        session_id,
        limit=limit,
        offset=offset,
    )
    return Response.success(
        data=[ToolExecutionResponse.model_validate(e) for e in executions],
        message="Tool executions retrieved successfully",
    )


@router.get(
    "/{session_id}/computer/browser/{tool_use_id}",
    response_model=ResponseSchema[ComputerBrowserScreenshotResponse],
)
async def get_session_browser_screenshot(
    session_id: uuid.UUID,
    tool_use_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return a presigned URL for a browser screenshot (Poco Computer)."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    key = build_browser_screenshot_key(
        user_id=user_id,
        session_id=str(session_id),
        tool_use_id=tool_use_id,
    )
    if not storage_service.exists(key):
        raise HTTPException(status_code=404, detail="Browser screenshot not ready")
    url = storage_service.presign_get(
        key,
        response_content_disposition="inline",
        response_content_type="image/png",
    )

    return Response.success(
        data=ComputerBrowserScreenshotResponse(tool_use_id=tool_use_id, url=url),
        message="Browser screenshot URL generated",
    )


@router.get("/{session_id}/usage", response_model=ResponseSchema[UsageResponse])
async def get_session_usage(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets usage statistics for a session."""
    # Verify session exists
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    usage = usage_service.get_usage_summary(db, session_id)
    return Response.success(
        data=usage,
        message="Usage statistics retrieved successfully",
    )


@router.get(
    "/{session_id}/workspace/files",
    response_model=ResponseSchema[list[FileNode]],
)
async def get_session_workspace_files(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List workspace files for a session (served via OSS manifest)."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    if not db_session.workspace_manifest_key:
        return Response.success(data=[], message="Workspace export not ready")

    manifest = storage_service.get_manifest(db_session.workspace_manifest_key)
    raw_nodes = build_nodes_from_manifest(manifest)
    manifest_files = extract_manifest_files(manifest)
    prefix = (db_session.workspace_files_prefix or "").rstrip("/")
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

    nodes = build_workspace_file_nodes(
        raw_nodes,
        file_url_builder=build_file_url,
    )
    return Response.success(data=nodes, message="Workspace files retrieved")


@router.get(
    "/{session_id}/workspace/archive",
    response_model=ResponseSchema[WorkspaceArchiveResponse],
)
async def get_session_workspace_archive(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get a presigned download URL for the exported workspace archive."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    filename = f"workspace-{session_id}.zip"
    archive_key = (db_session.workspace_archive_key or "").strip()
    if not archive_key or db_session.workspace_export_status != "ready":
        return Response.success(
            data=WorkspaceArchiveResponse(url=None, filename=filename),
            message="Workspace export not ready",
        )

    url = storage_service.presign_get(
        archive_key,
        response_content_disposition=f'attachment; filename="{filename}"',
        response_content_type="application/zip",
    )
    return Response.success(
        data=WorkspaceArchiveResponse(url=url, filename=filename),
        message="Workspace archive URL generated",
    )
