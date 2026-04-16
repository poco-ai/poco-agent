import re

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.computer import ComputerScreenshotUploadResponse
from app.services.storage_service import S3StorageService
from app.services.workspace_manager import WorkspaceManager


_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_token(value: str) -> str:
    token = (value or "").strip()
    token = _SAFE_TOKEN.sub("_", token)
    token = token.strip("._-")
    return token or "unknown"


class ComputerService:
    """Service layer for Poco Computer artifacts (screenshots, recordings, etc.)."""

    def __init__(
        self,
        *,
        workspace_manager: WorkspaceManager | None = None,
        storage_service: S3StorageService | None = None,
    ) -> None:
        self._workspace_manager = workspace_manager or WorkspaceManager()
        self._storage_service = storage_service or S3StorageService()

    def upload_browser_screenshot(
        self,
        *,
        session_id: str,
        run_id: str | None,
        tool_use_id: str,
        content_type: str,
        data: bytes,
    ) -> ComputerScreenshotUploadResponse:
        user_id = self._workspace_manager.resolve_user_id(session_id)
        if not user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Unable to resolve user_id for session",
                details={"session_id": session_id},
            )

        safe_session_id = _sanitize_token(session_id)
        safe_tool_use_id = _sanitize_token(tool_use_id)
        safe_run_id = _sanitize_token(run_id) if run_id else None

        # Keep both keys so session-scoped and run-scoped viewers can resolve screenshots.
        key = f"replays/{user_id}/{safe_session_id}/browser/{safe_tool_use_id}.png"
        run_key = (
            f"replays/{user_id}/{safe_session_id}/runs/{safe_run_id}/browser/"
            f"{safe_tool_use_id}.png"
            if safe_run_id
            else None
        )

        self._storage_service.put_object(
            key=key,
            body=data,
            content_type=content_type or "image/png",
        )
        if run_key:
            self._storage_service.put_object(
                key=run_key,
                body=data,
                content_type=content_type or "image/png",
            )

        return ComputerScreenshotUploadResponse(
            session_id=session_id,
            run_id=run_id,
            tool_use_id=tool_use_id,
            key=run_key or key,
            content_type=content_type or "image/png",
            size_bytes=len(data),
        )
