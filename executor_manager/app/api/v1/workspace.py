from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace import FileNode
from app.services.workspace_manager import WorkspaceManager

router = APIRouter(prefix="/workspace", tags=["workspace"])

_workspace_manager: WorkspaceManager | None = None


def get_workspace_manager() -> WorkspaceManager:
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager


@router.get("/stats", response_model=ResponseSchema[dict])
async def get_workspace_stats() -> JSONResponse:
    """Get workspace disk usage statistics."""
    stats = get_workspace_manager().get_disk_usage()
    return Response.success(data=stats)


@router.get("/users/{user_id}", response_model=ResponseSchema[list])
async def get_user_workspaces(user_id: str) -> JSONResponse:
    """Get all workspaces for a user."""
    workspaces = get_workspace_manager().get_user_workspaces(user_id)
    return Response.success(data=workspaces)


@router.post("/archive/{user_id}/{session_id}", response_model=ResponseSchema[dict])
async def archive_workspace(
    user_id: str,
    session_id: str,
    keep_days: int = Query(default=7, ge=1, le=90),
) -> JSONResponse:
    """Archive workspace."""
    archive_path = get_workspace_manager().archive_workspace(
        user_id=user_id,
        session_id=session_id,
        keep_days=keep_days,
    )

    if archive_path:
        return Response.success(
            data={"archive_path": archive_path},
            message="Workspace archived successfully",
        )
    else:
        raise AppException(error_code=ErrorCode.WORKSPACE_ARCHIVE_FAILED)


@router.delete("/{user_id}/{session_id}", response_model=ResponseSchema[dict])
async def delete_workspace(
    user_id: str,
    session_id: str,
    force: bool = Query(default=False),
) -> JSONResponse:
    """Delete workspace."""
    success = get_workspace_manager().delete_workspace(
        user_id=user_id,
        session_id=session_id,
        force=force,
    )

    if success:
        return Response.success(
            data={"user_id": user_id, "session_id": session_id},
            message="Workspace deleted successfully",
        )
    else:
        raise AppException(error_code=ErrorCode.WORKSPACE_DELETE_FAILED)


@router.get(
    "/files/{user_id}/{session_id}",
    response_model=ResponseSchema[list[FileNode]],
)
async def list_workspace_files(user_id: str, session_id: str) -> JSONResponse:
    """List workspace files for a session."""
    files = get_workspace_manager().list_workspace_files(
        user_id=user_id, session_id=session_id
    )
    return Response.success(data=files)


@router.get("/file/{user_id}/{session_id}")
async def get_workspace_file(
    user_id: str,
    session_id: str,
    path: str = Query(..., description="File path within the workspace"),
) -> FileResponse:
    """Serve a single file from workspace for preview/download."""
    file_path = get_workspace_manager().resolve_workspace_file(
        user_id=user_id, session_id=session_id, file_path=path
    )
    if not file_path:
        raise AppException(error_code=ErrorCode.WORKSPACE_NOT_FOUND)

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        content_disposition_type="inline",
    )
