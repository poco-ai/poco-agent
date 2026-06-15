import uuid
import shutil
from datetime import datetime
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response as FastAPIResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.message import (
    MessageAttachmentsDeltaResponse,
    MessageAttachmentsResponse,
    MessageDeltaResponse,
    MessageWithFilesDeltaResponse,
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
from app.schemas.tool_execution import ToolExecutionDeltaResponse, ToolExecutionResponse
from app.schemas.usage import UsageResponse
from app.schemas.workspace import FileNode, WorkspaceArchiveResponse
from app.schemas.workspace import SubmitSkillRequest, SubmitSkillResponse
from app.services.message_service import MessageService
from app.services.local_mount_browser_service import LocalMountBrowserService
from app.services.pending_skill_creation_service import PendingSkillCreationService
from app.services.session_service import SessionService
from app.services.storage_service import S3StorageService
from app.services.tool_execution_service import ToolExecutionService
from app.services.usage_service import UsageService
from app.services.workspace_archive_service import WorkspaceArchiveService
from app.utils.computer import build_browser_screenshot_key
from app.utils.workspace_export import (
    build_workspace_file_nodes_from_export,
    create_workspace_preview_token,
    resolve_export_object_key,
    verify_workspace_preview_token,
)
from app.utils.workspace_manifest import (
    find_manifest_file,
    normalize_manifest_path,
)
from app.utils.mime import guess_mime_type

router = APIRouter(prefix="/sessions", tags=["sessions"])

session_service = SessionService()
message_service = MessageService()
tool_execution_service = ToolExecutionService()
usage_service = UsageService()
storage_service = S3StorageService()
pending_skill_creation_service = PendingSkillCreationService()
workspace_archive_service = WorkspaceArchiveService()
local_mount_browser_service = LocalMountBrowserService()


def _local_mount_file_url(
    *,
    session_id: uuid.UUID,
    mount_id: str,
    path: str,
) -> str:
    query = urlencode({"mount_id": mount_id, "path": path, "disposition": "inline"})
    return f"/api/v1/sessions/{session_id}/local-mounts/file?{query}"


def _attach_local_mount_file_urls(
    *,
    session_id: uuid.UUID,
    nodes: list[FileNode],
) -> list[FileNode]:
    result: list[FileNode] = []
    for node in nodes:
        children = (
            _attach_local_mount_file_urls(session_id=session_id, nodes=node.children)
            if node.children
            else None
        )
        url = node.url
        if node.type == "file" and node.mount_id:
            url = _local_mount_file_url(
                session_id=session_id,
                mount_id=node.mount_id,
                path=node.path,
            )
        result.append(node.model_copy(update={"children": children, "url": url}))
    return result


def _workspace_export_file_url(
    *,
    session_id: uuid.UUID,
    path: str,
    preview_token: str,
) -> str | None:
    normalized = normalize_manifest_path(path)
    if not normalized:
        return None
    return (
        f"/api/v1/sessions/{session_id}/workspace/raw"
        f"/{quote(preview_token, safe='')}/{quote(normalized.lstrip('/'), safe='/')}"
    )


def _stream_workspace_export_file(
    *,
    manifest_key: str | None,
    workspace_files_prefix: str | None,
    path: str,
) -> FastAPIResponse:
    manifest_key = (manifest_key or "").strip()
    if not manifest_key:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message="Workspace export not ready",
        )

    normalized_path = normalize_manifest_path(path)
    if not normalized_path:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="Invalid workspace file path",
        )

    manifest = storage_service.get_manifest(manifest_key)
    file_entry = find_manifest_file(manifest, normalized_path)
    if file_entry is None:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message="Workspace file not found",
        )

    object_key = resolve_export_object_key(
        file_entry=file_entry,
        workspace_files_prefix=workspace_files_prefix,
    )
    if not object_key:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message="Workspace file object not found",
        )

    mime_type = (
        file_entry.get("mimeType")
        or file_entry.get("mime_type")
        or guess_mime_type(normalized_path)
        or "application/octet-stream"
    )
    return FastAPIResponse(
        content=storage_service.get_bytes(object_key),
        media_type=str(mime_type),
        headers={"Content-Disposition": "inline"},
    )


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
    """Cancel a session and let Executor Manager stop the active executor."""
    result = session_service.cancel_session(
        db,
        session_id,
        user_id=user_id,
        reason=request.reason,
    )

    return Response.success(
        data=result,
        message="Session cancellation requested successfully",
    )


@router.post(
    "/{session_id}/cancel-current-run",
    response_model=ResponseSchema[SessionCancelResponse],
)
async def cancel_current_run(
    session_id: uuid.UUID,
    request: SessionCancelRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Cancel the currently running execution and keep queued follow-ups intact."""
    result = session_service.cancel_current_execution(
        db,
        session_id,
        user_id=user_id,
        reason=request.reason,
    )

    return Response.success(
        data=result,
        message="Current execution cancellation requested successfully",
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
        model=request.model,
        model_provider_id=request.model_provider_id,
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
        model=request.model,
        model_provider_id=request.model_provider_id,
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
    "/{session_id}/messages/delta",
    response_model=ResponseSchema[MessageDeltaResponse],
)
async def get_session_messages_delta(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    after_message_id: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets incremental messages for a session without attachments."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    payload = message_service.get_messages_delta(
        db,
        session_id,
        after_message_id=after_message_id,
        limit=limit,
    )
    return Response.success(
        data=payload,
        message="Messages delta retrieved successfully",
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
    "/{session_id}/messages-with-files/delta",
    response_model=ResponseSchema[MessageWithFilesDeltaResponse],
)
async def get_session_messages_with_files_delta(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    after_message_id: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets incremental messages for a session with per-message attachments."""

    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    payload = message_service.get_messages_with_files_delta(
        db,
        session_id,
        user_id=user_id,
        after_message_id=after_message_id,
        limit=limit,
    )
    return Response.success(
        data=payload,
        message="Messages delta retrieved successfully",
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
    "/{session_id}/message-attachments/delta",
    response_model=ResponseSchema[MessageAttachmentsDeltaResponse],
)
async def get_session_message_attachments_delta(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    after_message_id: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets incremental per-message attachments for a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    payload = message_service.get_message_attachments_delta(
        db,
        session_id,
        user_id=user_id,
        after_message_id=after_message_id,
        limit=limit,
    )
    return Response.success(
        data=payload,
        message="Message attachments delta retrieved successfully",
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
    "/{session_id}/tool-executions/delta",
    response_model=ResponseSchema[ToolExecutionDeltaResponse],
)
async def get_session_tool_executions_delta(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    after_created_at: datetime | None = Query(default=None),
    after_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Gets incremental tool executions for a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )
    if after_id is not None and after_created_at is None:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="after_created_at is required when after_id is provided",
        )

    payload = tool_execution_service.get_tool_executions_delta(
        db,
        session_id,
        after_created_at=after_created_at,
        after_id=after_id,
        limit=limit,
    )
    return Response.success(
        data=payload,
        message="Tool executions delta retrieved successfully",
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

    preview_token = create_workspace_preview_token(
        scope="session",
        scope_id=str(session_id),
    )
    nodes = build_workspace_file_nodes_from_export(
        manifest_key=db_session.workspace_manifest_key,
        workspace_files_prefix=db_session.workspace_files_prefix,
        storage_service=storage_service,
        file_url_builder=lambda path: _workspace_export_file_url(
            session_id=session_id,
            path=path,
            preview_token=preview_token,
        ),
    )
    return Response.success(data=nodes, message="Workspace files retrieved")


@router.get("/{session_id}/workspace/raw/{preview_token}/{path:path}")
async def get_session_workspace_file(
    session_id: uuid.UUID,
    preview_token: str,
    path: str,
    db: Session = Depends(get_db),
) -> FastAPIResponse:
    """Stream a file from an exported workspace snapshot."""
    db_session = session_service.get_session(db, session_id)
    if not verify_workspace_preview_token(
        preview_token,
        scope="session",
        scope_id=str(session_id),
    ):
        raise HTTPException(status_code=401, detail="Authentication required")
    return _stream_workspace_export_file(
        manifest_key=db_session.workspace_manifest_key,
        workspace_files_prefix=db_session.workspace_files_prefix,
        path=path,
    )


@router.get(
    "/{session_id}/local-mounts/files",
    response_model=ResponseSchema[list[FileNode]],
)
async def get_session_local_mount_files(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List authorized local mount files for a session."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    nodes = local_mount_browser_service.list_files(db_session)
    nodes = _attach_local_mount_file_urls(session_id=session_id, nodes=nodes)
    return Response.success(data=nodes, message="Local mount files retrieved")


@router.get("/{session_id}/local-mounts/file")
async def get_session_local_mount_file(
    session_id: uuid.UUID,
    mount_id: str = Query(...),
    path: str = Query(...),
    disposition: str = Query(default="inline"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Stream a file from a session-authorized local mount."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    file_path, _ = local_mount_browser_service.resolve_file(
        db_session,
        mount_id=mount_id,
        path=path,
    )
    return FileResponse(
        path=file_path,
        media_type=guess_mime_type(file_path.name) or "application/octet-stream",
        filename=file_path.name,
        content_disposition_type="attachment"
        if disposition == "attachment"
        else "inline",
    )


@router.get(
    "/{session_id}/local-mounts/folder-archive",
    response_model=ResponseSchema[WorkspaceArchiveResponse],
)
async def get_session_local_mount_folder_archive(
    session_id: uuid.UUID,
    mount_id: str = Query(...),
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get a same-origin download URL for an authorized local mount folder archive."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    filename = local_mount_browser_service.build_archive_filename(
        config=local_mount_browser_service.get_session_mount_config(db_session),
        mount_id=mount_id,
        path=path,
    )
    query = urlencode({"mount_id": mount_id, "path": path})
    return Response.success(
        data=WorkspaceArchiveResponse(
            url=f"/api/v1/sessions/{session_id}/local-mounts/archive?{query}",
            filename=filename,
        ),
        message="Local mount folder archive URL generated",
    )


@router.get("/{session_id}/local-mounts/archive")
async def download_session_local_mount_archive(
    session_id: uuid.UUID,
    mount_id: str = Query(...),
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create and stream a temporary zip archive for an authorized local mount folder."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    archive_path, filename = local_mount_browser_service.create_folder_archive(
        db_session,
        mount_id=mount_id,
        path=path,
    )

    def cleanup_archive() -> None:
        try:
            archive_path.unlink(missing_ok=True)
        finally:
            shutil.rmtree(archive_path.parent, ignore_errors=True)

    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(cleanup_archive),
    )


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


@router.get(
    "/{session_id}/workspace/folder-archive",
    response_model=ResponseSchema[WorkspaceArchiveResponse],
)
async def get_session_workspace_folder_archive(
    session_id: uuid.UUID,
    path: str = Query(..., description="Folder path within the workspace"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get a presigned download URL for a workspace folder archive."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    normalized_path = normalize_manifest_path(path)
    folder_name = (
        normalized_path.strip("/").split("/")[-1]
        if normalized_path
        else f"workspace-{session_id}"
    )
    filename = f"{folder_name or f'workspace-{session_id}'}.zip"

    if db_session.workspace_export_status != "ready":
        return Response.success(
            data=WorkspaceArchiveResponse(url=None, filename=filename),
            message="Workspace export not ready",
        )

    archive = workspace_archive_service.get_folder_archive(
        session=db_session,
        folder_path=path,
    )
    return Response.success(
        data=archive,
        message="Workspace folder archive URL generated",
    )


@router.post(
    "/{session_id}/workspace/submit-skill",
    response_model=ResponseSchema[SubmitSkillResponse],
)
async def submit_session_workspace_skill(
    session_id: uuid.UUID,
    request: SubmitSkillRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Submit a workspace folder for skill creation review."""
    db_session = session_service.get_session(db, session_id)
    if db_session.user_id != user_id:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Session does not belong to the user",
        )

    pending = pending_skill_creation_service.submit_from_workspace(
        db,
        user_id=user_id,
        session=db_session,
        folder_path=request.folder_path,
        skill_name=request.skill_name,
    )
    db.commit()
    db.refresh(pending)
    return Response.success(
        data=SubmitSkillResponse(
            pending_id=str(pending.id),
            status=pending.status,
        ),
        message="Skill submission queued successfully",
    )
