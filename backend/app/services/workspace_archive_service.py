import hashlib
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.schemas.workspace import WorkspaceArchiveResponse
from app.services.storage_service import S3StorageService
from app.utils.workspace_manifest import (
    extract_manifest_files,
    normalize_manifest_path,
)


class WorkspaceArchiveService:
    """Create downloadable archives for exported workspace content."""

    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service

    def get_folder_archive(
        self,
        *,
        session: AgentSession,
        folder_path: str,
    ) -> WorkspaceArchiveResponse:
        normalized_folder_path = self._normalize_folder_path(folder_path)
        filename = self._build_archive_filename(normalized_folder_path)

        self._require_workspace_export_ready(session)

        manifest_key = (session.workspace_manifest_key or "").strip()
        if not manifest_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace manifest is not available",
            )

        manifest = self._storage_service().get_manifest(manifest_key)
        workspace_prefix = self._require_workspace_files_prefix(session)
        file_entries = self._collect_folder_files(
            manifest=manifest,
            folder_path=normalized_folder_path,
        )
        if not file_entries:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Workspace folder is empty or unavailable",
            )

        archive_key = self._build_archive_key(
            session=session,
            folder_path=normalized_folder_path,
        )
        self._create_and_upload_archive(
            archive_key=archive_key,
            filename=filename,
            folder_path=normalized_folder_path,
            workspace_prefix=workspace_prefix,
            file_entries=file_entries,
        )

        url = self._storage_service().presign_get(
            archive_key,
            response_content_disposition=f'attachment; filename="{filename}"',
            response_content_type="application/zip",
        )
        return WorkspaceArchiveResponse(url=url, filename=filename)

    @staticmethod
    def _normalize_folder_path(folder_path: str) -> str:
        normalized = normalize_manifest_path(folder_path)
        if not normalized:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid workspace folder path",
            )
        return normalized

    @staticmethod
    def _build_archive_filename(folder_path: str) -> str:
        folder_name = PurePosixPath(folder_path).name or "workspace"
        safe_name = "".join(
            character
            for character in folder_name
            if character.isalnum() or character in {"-", "_", "."}
        ).strip("._")
        return f"{safe_name or 'workspace'}.zip"

    @staticmethod
    def _build_archive_key(*, session: AgentSession, folder_path: str) -> str:
        digest = hashlib.sha256(folder_path.encode("utf-8")).hexdigest()[:16]
        return f"workspaces/{session.user_id}/{session.id}/folder-archives/{digest}.zip"

    @staticmethod
    def _extract_object_key(file_entry: dict) -> str | None:
        for key in ("key", "object_key", "oss_key", "s3_key"):
            value = file_entry.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    @staticmethod
    def _require_workspace_files_prefix(session: AgentSession) -> str:
        workspace_prefix = (session.workspace_files_prefix or "").strip().rstrip("/")
        if not workspace_prefix:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace files prefix is missing",
            )
        return workspace_prefix

    @staticmethod
    def _require_workspace_export_ready(session: AgentSession) -> None:
        if (session.workspace_export_status or "").strip().lower() != "ready":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace export not ready",
            )

    def _collect_folder_files(
        self,
        *,
        manifest: dict,
        folder_path: str,
    ) -> list[dict]:
        folder_prefix = f"{folder_path.rstrip('/')}/"
        matched: list[dict] = []
        for file_entry in extract_manifest_files(manifest):
            normalized_path = normalize_manifest_path(file_entry.get("path"))
            if not normalized_path or not normalized_path.startswith(folder_prefix):
                continue
            matched.append(file_entry)
        return matched

    def _create_and_upload_archive(
        self,
        *,
        archive_key: str,
        filename: str,
        folder_path: str,
        workspace_prefix: str,
        file_entries: list[dict],
    ) -> None:
        folder_root = PurePosixPath(folder_path).name or "workspace"

        with tempfile.TemporaryDirectory(
            prefix="workspace-folder-archive-"
        ) as temp_dir:
            temp_root = Path(temp_dir)
            download_root = temp_root / "download"
            archive_path = temp_root / filename

            with zipfile.ZipFile(
                archive_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for file_entry in file_entries:
                    normalized_path = normalize_manifest_path(file_entry.get("path"))
                    if not normalized_path:
                        continue

                    object_key = self._extract_object_key(file_entry)
                    if not object_key:
                        object_key = f"{workspace_prefix}/{normalized_path.lstrip('/')}"

                    relative_path = PurePosixPath(
                        normalized_path.lstrip("/")
                    ).relative_to(PurePosixPath(folder_path.lstrip("/")))
                    local_path = download_root / relative_path.as_posix()
                    self._storage_service().download_file(
                        key=object_key,
                        destination=local_path,
                    )
                    archive.write(
                        local_path,
                        arcname=f"{folder_root}/{relative_path.as_posix()}",
                    )

            self._storage_service().upload_file(
                file_path=str(archive_path),
                key=archive_key,
                content_type="application/zip",
            )

    def _storage_service(self) -> S3StorageService:
        if self.storage_service is None:
            self.storage_service = S3StorageService()
        return self.storage_service
