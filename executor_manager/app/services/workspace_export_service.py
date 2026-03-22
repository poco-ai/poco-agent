import json
import logging
import mimetypes
import os
import shutil
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.schemas.workspace import WorkspaceExportResult
from app.services.storage_service import S3StorageService
from app.services.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)


workspace_manager = WorkspaceManager()
storage_service = S3StorageService()
_ALLOWED_HIDDEN_SKILL_ROOTS = frozenset({".config", ".config_data"})
_SKILL_VISIBLE_ROOT = PurePosixPath("/.config/skills")
_VISIBLE_DRAFT_ROOT = PurePosixPath("/skills")


class WorkspaceExportService:
    def export_workspace(self, session_id: str) -> WorkspaceExportResult:
        user_id = workspace_manager.resolve_user_id(session_id)
        if not user_id:
            return WorkspaceExportResult(
                error="Unable to resolve user_id for session",
                workspace_export_status="failed",
            )

        workspace_dir = workspace_manager.get_session_workspace_dir(
            user_id=user_id, session_id=session_id
        )
        if not workspace_dir:
            return WorkspaceExportResult(
                error="Workspace directory not found",
                workspace_export_status="failed",
            )

        prefix = f"workspaces/{user_id}/{session_id}"
        files_prefix = f"{prefix}/files"
        manifest_key = f"{prefix}/manifest.json"
        archive_key = f"{prefix}/archive.zip"

        try:
            files = self._collect_files(workspace_dir)
            manifest = {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "files": [],
            }

            for file_path in files:
                rel_path = file_path.relative_to(workspace_dir).as_posix()
                object_key = f"{files_prefix}/{rel_path}"
                mime_type, _ = mimetypes.guess_type(file_path.name)

                storage_service.upload_file(
                    file_path=str(file_path),
                    key=object_key,
                    content_type=mime_type,
                )

                manifest["files"].append(
                    {
                        "path": rel_path,
                        "key": object_key,
                        "size": file_path.stat().st_size,
                        "mimeType": mime_type,
                        "status": "uploaded",
                        "last_modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )

            storage_service.put_object(
                key=manifest_key,
                body=json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
            )

            archive_path = self._create_archive(
                workspace_dir=workspace_dir,
                session_id=session_id,
                files=files,
            )
            storage_service.upload_file(
                file_path=str(archive_path),
                key=archive_key,
                content_type="application/zip",
            )

            try:
                archive_path.unlink(missing_ok=True)
            except Exception:
                logger.warning(f"Failed to cleanup archive temp file: {archive_path}")

            return WorkspaceExportResult(
                workspace_files_prefix=files_prefix,
                workspace_manifest_key=manifest_key,
                workspace_archive_key=archive_key,
                workspace_export_status="ready",
            )
        except AppException as exc:
            logger.error(f"Workspace export failed: {exc.message}")
            return WorkspaceExportResult(
                error=exc.message, workspace_export_status="failed"
            )
        except Exception as exc:
            logger.error(f"Workspace export failed: {exc}")
            return WorkspaceExportResult(
                error=str(exc), workspace_export_status="failed"
            )

    def stage_skill_submission_folder(
        self,
        session_id: str,
        *,
        folder_path: str,
    ) -> str:
        user_id = workspace_manager.resolve_user_id(session_id)
        if not user_id:
            raise AppException(
                error_code=ErrorCode.WORKSPACE_NOT_FOUND,
                message="Unable to resolve user_id for session",
            )

        workspace_dir = workspace_manager.get_session_workspace_dir(
            user_id=user_id, session_id=session_id
        )
        if not workspace_dir:
            raise AppException(
                error_code=ErrorCode.WORKSPACE_NOT_FOUND,
                message="Workspace directory not found",
            )

        normalized_folder_path = self._normalize_workspace_path(folder_path)
        source_dir = self._resolve_workspace_dir(
            workspace_dir=workspace_dir,
            relative_path=normalized_folder_path,
        )
        if not source_dir.exists() or not source_dir.is_dir():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Skill folder not found in workspace",
            )
        if not (source_dir / "SKILL.md").is_file():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Skill folder must contain SKILL.md",
            )

        normalized_folder_path, source_dir = self._prefer_visible_workspace_draft(
            workspace_dir=workspace_dir,
            normalized_folder_path=normalized_folder_path,
            source_dir=source_dir,
        )

        if self._is_visible_skill_folder(normalized_folder_path):
            return normalized_folder_path

        destination_path = (
            _SKILL_VISIBLE_ROOT / PurePosixPath(normalized_folder_path).name
        ).as_posix()
        destination_dir = self._resolve_workspace_dir(
            workspace_dir=workspace_dir,
            relative_path=destination_path,
            create_parent=True,
        )

        if source_dir.resolve() != destination_dir.resolve():
            if destination_dir.exists():
                shutil.rmtree(destination_dir)
            shutil.copytree(source_dir, destination_dir)

        return destination_path

    def export_workspace_folder(
        self,
        session_id: str,
        *,
        folder_path: str,
    ) -> WorkspaceExportResult:
        user_id = workspace_manager.resolve_user_id(session_id)
        if not user_id:
            return WorkspaceExportResult(
                error="Unable to resolve user_id for session",
                workspace_export_status="failed",
            )

        workspace_dir = workspace_manager.get_session_workspace_dir(
            user_id=user_id, session_id=session_id
        )
        if not workspace_dir:
            return WorkspaceExportResult(
                error="Workspace directory not found",
                workspace_export_status="failed",
            )

        try:
            normalized_folder_path = self._normalize_workspace_path(folder_path)
            folder_dir = self._resolve_workspace_dir(
                workspace_dir=workspace_dir,
                relative_path=normalized_folder_path,
            )
            if not folder_dir.exists() or not folder_dir.is_dir():
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Workspace folder not found",
                )

            files = self._collect_folder_files(
                workspace_dir=workspace_dir,
                folder_dir=folder_dir,
            )
            if not files:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Workspace folder is empty",
                )

            digest = sha256(normalized_folder_path.encode("utf-8")).hexdigest()[:16]
            prefix = f"workspaces/{user_id}/{session_id}/skill-submissions/{digest}"
            files_prefix = f"{prefix}/files"
            manifest_key = f"{prefix}/manifest.json"
            manifest = {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "files": [],
            }

            for file_path in files:
                rel_path = file_path.relative_to(workspace_dir).as_posix()
                object_key = f"{files_prefix}/{rel_path}"
                mime_type, _ = mimetypes.guess_type(file_path.name)
                storage_service.upload_file(
                    file_path=str(file_path),
                    key=object_key,
                    content_type=mime_type,
                )
                manifest["files"].append(
                    {
                        "path": rel_path,
                        "key": object_key,
                        "size": file_path.stat().st_size,
                        "mimeType": mime_type,
                        "status": "uploaded",
                        "last_modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    }
                )

            storage_service.put_object(
                key=manifest_key,
                body=json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
            )
            return WorkspaceExportResult(
                workspace_files_prefix=files_prefix,
                workspace_manifest_key=manifest_key,
                workspace_export_status="ready",
            )
        except AppException as exc:
            logger.error(f"Workspace folder export failed: {exc.message}")
            return WorkspaceExportResult(
                error=exc.message, workspace_export_status="failed"
            )
        except Exception as exc:
            logger.error(f"Workspace folder export failed: {exc}")
            return WorkspaceExportResult(
                error=str(exc), workspace_export_status="failed"
            )

    def _collect_files(self, workspace_dir: Path) -> list[Path]:
        files: list[Path] = []
        ignore_names = workspace_manager._ignore_names
        ignore_dot = workspace_manager.ignore_dot_files

        for root, dirnames, filenames in os.walk(workspace_dir):
            root_path = Path(root)
            dirnames[:] = [
                d
                for d in dirnames
                if not self._should_skip(
                    root_path / d,
                    workspace_dir=workspace_dir,
                    ignore_names=ignore_names,
                    ignore_dot=ignore_dot,
                )
            ]
            for filename in filenames:
                file_path = root_path / filename
                if self._should_skip(
                    file_path,
                    workspace_dir=workspace_dir,
                    ignore_names=ignore_names,
                    ignore_dot=ignore_dot,
                ):
                    continue
                if file_path.is_symlink():
                    continue
                if not file_path.is_file():
                    continue
                files.append(file_path)

        return files

    @staticmethod
    def _collect_folder_files(*, workspace_dir: Path, folder_dir: Path) -> list[Path]:
        files: list[Path] = []
        for root, _, filenames in os.walk(folder_dir):
            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                if file_path.is_symlink() or not file_path.is_file():
                    continue
                file_path.relative_to(workspace_dir)
                files.append(file_path)
        return files

    def _create_archive(
        self,
        *,
        workspace_dir: Path,
        session_id: str,
        files: list[Path],
    ) -> Path:
        temp_dir = workspace_manager.temp_dir
        temp_dir.mkdir(parents=True, exist_ok=True)
        archive_path = temp_dir / f"{session_id}.zip"

        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zipf:
            for file_path in files:
                rel_path = file_path.relative_to(workspace_dir).as_posix()
                zipf.write(file_path, arcname=f"workspace/{rel_path}")

        return archive_path

    @staticmethod
    def _normalize_workspace_path(path: str) -> str:
        normalized = (path or "").replace("\\", "/").strip()
        if not normalized:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid workspace folder path",
            )
        if normalized == "/workspace":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Skill folder path must point to a folder, not /workspace",
            )
        if normalized.startswith("/workspace/"):
            normalized = normalized[len("/workspace/") :]
        normalized = "/" + normalized.lstrip("/")
        parts = [part for part in normalized.split("/") if part]
        if not parts or any(part in {".", ".."} for part in parts):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid workspace folder path",
            )
        return "/" + "/".join(parts)

    @staticmethod
    def _resolve_workspace_dir(
        *,
        workspace_dir: Path,
        relative_path: str,
        create_parent: bool = False,
    ) -> Path:
        clean = relative_path.lstrip("/")
        candidate = (workspace_dir / clean).resolve()
        base = workspace_dir.resolve()
        try:
            candidate.relative_to(base)
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace folder path escapes workspace",
            ) from exc
        if create_parent:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    @staticmethod
    def _is_visible_skill_folder(path: str) -> bool:
        parts = PurePosixPath(path).parts
        return len(parts) == 4 and parts[1] == ".config" and parts[2] == "skills"

    @staticmethod
    def _prefer_visible_workspace_draft(
        *,
        workspace_dir: Path,
        normalized_folder_path: str,
        source_dir: Path,
    ) -> tuple[str, Path]:
        if not WorkspaceExportService._is_visible_skill_folder(normalized_folder_path):
            return normalized_folder_path, source_dir

        skill_name = source_dir.name
        visible_draft_path = (_VISIBLE_DRAFT_ROOT / skill_name).as_posix()
        visible_draft_dir = WorkspaceExportService._resolve_workspace_dir(
            workspace_dir=workspace_dir,
            relative_path=visible_draft_path,
        )
        if not visible_draft_dir.is_dir():
            return normalized_folder_path, source_dir
        if not (visible_draft_dir / "SKILL.md").is_file():
            return normalized_folder_path, source_dir
        return visible_draft_path, visible_draft_dir

    @staticmethod
    def _is_allowed_hidden_skill_path(path: Path, workspace_dir: Path) -> bool:
        try:
            relative_parts = path.relative_to(workspace_dir).parts
        except Exception:
            return False

        if not relative_parts:
            return False
        if relative_parts[0] not in _ALLOWED_HIDDEN_SKILL_ROOTS:
            return False
        if len(relative_parts) == 1:
            return True
        return relative_parts[1] == "skills"

    @classmethod
    def _should_skip(
        cls,
        path: Path,
        *,
        workspace_dir: Path,
        ignore_names: set[str],
        ignore_dot: bool,
    ) -> bool:
        name = path.name
        if name in ignore_names:
            return True
        if ignore_dot and name.startswith("."):
            if not cls._is_allowed_hidden_skill_path(path, workspace_dir):
                return True
        if path.is_symlink():
            return True
        return False
