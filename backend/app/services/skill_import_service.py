import mimetypes
import os
import re
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, IO, Iterable

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.skill import Skill
from app.models.user_skill_install import UserSkillInstall
from app.repositories.skill_repository import SkillRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.skill_import import (
    SkillImportCandidate,
    SkillImportCommitRequest,
    SkillImportCommitResponse,
    SkillImportDiscoverResponse,
    SkillImportResultItem,
)
from app.services.storage_service import S3StorageService


_SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_FILENAME_CLEAN = re.compile(r"[^a-zA-Z0-9._-]+")
_MAX_FILES_PER_SKILL = 5000
_MAX_UNCOMPRESSED_BYTES_PER_SKILL = 500 * 1024 * 1024


def _sanitize_filename(filename: str) -> str:
    clean = os.path.basename(filename or "").strip()
    clean = _FILENAME_CLEAN.sub("_", clean)
    return clean or "upload.zip"


def _validate_skill_name(name: str) -> str:
    value = (name or "").strip()
    if not value or value in {".", ".."} or not _SKILL_NAME_PATTERN.fullmatch(value):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid skill name: {name}",
        )
    return value


def _safe_relative_path(value: str) -> PurePosixPath:
    raw = (value or "").strip()
    if not raw:
        raw = "."
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid relative path: {value}",
        )
    return path


def _is_ignored_path(path: PurePosixPath) -> bool:
    # Common junk files in zip exports on macOS.
    if "__MACOSX" in path.parts:
        return True
    if path.name == ".DS_Store":
        return True
    return False


def _extract_common_root(names: Iterable[str]) -> str | None:
    first_parts: set[str] = set()
    for name in names:
        p = PurePosixPath(name)
        if not p.parts:
            continue
        first_parts.add(p.parts[0])
        if len(first_parts) > 1:
            return None
    return next(iter(first_parts)) if first_parts else None


def _strip_common_root(path: PurePosixPath, common_root: str | None) -> PurePosixPath:
    if common_root and path.parts and path.parts[0] == common_root:
        try:
            return path.relative_to(common_root)
        except Exception:
            return path
    return path


class SkillImportService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service or S3StorageService()

    def discover(
        self,
        db: Session,
        *,
        user_id: str,
        file: UploadFile | None,
        github_url: str | None,
    ) -> SkillImportDiscoverResponse:
        if bool(file) == bool(github_url):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Exactly one of file or github_url must be provided",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path: Path | None = None
            source_bytes: IO[bytes] | None = None
            source_name: str = "upload.zip"

            if file is not None:
                filename = _sanitize_filename(file.filename or "upload.zip")
                if not filename.lower().endswith(".zip"):
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message="Only .zip archives are supported",
                    )
                max_size_bytes = get_settings().max_upload_size_mb * 1024 * 1024
                size = self._get_upload_size(file)
                if size is not None and size > max_size_bytes:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message=f"File too large. Max {get_settings().max_upload_size_mb}MB.",
                        details={"max_bytes": max_size_bytes, "actual_bytes": size},
                    )
                file.file.seek(0)
                source_bytes = file.file
                source_name = filename
            else:
                github_url = (github_url or "").strip()
                if not github_url:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message="github_url cannot be empty",
                    )
                source_path = tmp_root / "github.zip"
                self._download_github_zip(
                    github_url=github_url, destination=source_path
                )
                source_name = "github.zip"

            candidates = self._scan_candidates(
                zip_source_path=source_path, zip_source_bytes=source_bytes
            )
            if not candidates:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="No SKILL.md found in the archive",
                )

            # Compute overwrite flags using DB.
            response_candidates: list[SkillImportCandidate] = []
            for c in candidates:
                skill_name = c["skill_name"]
                will_overwrite = (
                    bool(skill_name)
                    and SkillRepository.get_by_name(db, skill_name, user_id) is not None
                )
                response_candidates.append(
                    SkillImportCandidate(
                        relative_path=c["relative_path"],
                        skill_name=skill_name,
                        requires_name=c["requires_name"],
                        will_overwrite=will_overwrite,
                    )
                )

            archive_key = self._upload_archive(
                user_id=user_id,
                filename=source_name,
                source_path=source_path,
                source_bytes=source_bytes,
            )

            # Persist minimal provenance (optional) by encoding into the key is not necessary.
            # Keep it in response for the caller if needed later.
            return SkillImportDiscoverResponse(
                archive_key=archive_key,
                candidates=response_candidates,
            )

    def commit(
        self, db: Session, *, user_id: str, request: SkillImportCommitRequest
    ) -> SkillImportCommitResponse:
        archive_key = (request.archive_key or "").strip()
        if not archive_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="archive_key cannot be empty",
            )
        self._require_archive_owner(user_id=user_id, archive_key=archive_key)

        if not request.selections:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="selections cannot be empty",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            zip_path = tmp_root / "archive.zip"
            self.storage_service.download_file(key=archive_key, destination=zip_path)

            try:
                zipf = zipfile.ZipFile(zip_path)
            except zipfile.BadZipFile as exc:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Invalid zip archive",
                ) from exc

            with zipf:
                candidates = self._scan_candidates(
                    zip_source_path=zip_path, zip_source_bytes=None
                )
                candidate_by_path = {c["relative_path"]: c for c in candidates}
                candidate_dirs = [
                    _safe_relative_path(c["relative_path"]) for c in candidates
                ]

                seen: set[str] = set()
                items: list[SkillImportResultItem] = []
                for selection in request.selections:
                    rel_raw = (selection.relative_path or "").strip() or "."
                    if rel_raw in seen:
                        continue
                    seen.add(rel_raw)
                    try:
                        item = self._import_one(
                            db=db,
                            user_id=user_id,
                            zipf=zipf,
                            candidate_by_path=candidate_by_path,
                            candidate_dirs=candidate_dirs,
                            relative_path=rel_raw,
                            name_override=selection.name_override,
                            archive_key=archive_key,
                        )
                        items.append(item)
                    except AppException as exc:
                        db.rollback()
                        items.append(
                            SkillImportResultItem(
                                relative_path=rel_raw,
                                status="failed",
                                error=str(exc.message),
                            )
                        )
                    except Exception as exc:
                        db.rollback()
                        items.append(
                            SkillImportResultItem(
                                relative_path=rel_raw,
                                status="failed",
                                error=str(exc),
                            )
                        )

                return SkillImportCommitResponse(items=items)

    @staticmethod
    def _get_upload_size(file: UploadFile) -> int | None:
        try:
            file.file.seek(0, os.SEEK_END)
            size = file.file.tell()
            file.file.seek(0)
            return size
        except Exception:
            return None

    def _upload_archive(
        self,
        *,
        user_id: str,
        filename: str,
        source_path: Path | None,
        source_bytes: IO[bytes] | None,
    ) -> str:
        archive_id = str(uuid.uuid4())
        safe_name = _sanitize_filename(filename)
        key = f"skill-imports/{user_id}/{archive_id}/{safe_name}"

        if source_path is not None:
            with source_path.open("rb") as f:
                self.storage_service.upload_fileobj(
                    fileobj=f, key=key, content_type="application/zip"
                )
            return key
        if source_bytes is not None:
            try:
                source_bytes.seek(0)
            except Exception:
                pass
            self.storage_service.upload_fileobj(
                fileobj=source_bytes, key=key, content_type="application/zip"
            )
            return key

        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message="No archive source provided",
        )

    @staticmethod
    def _require_archive_owner(*, user_id: str, archive_key: str) -> None:
        expected_prefix = f"skill-imports/{user_id}/"
        if not archive_key.startswith(expected_prefix):
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Archive does not belong to the user",
            )

    @staticmethod
    def _scan_candidates(
        *,
        zip_source_path: Path | None,
        zip_source_bytes: IO[bytes] | None,
    ) -> list[dict[str, Any]]:
        if bool(zip_source_path) == bool(zip_source_bytes):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Exactly one zip source must be provided",
            )

        try:
            if zip_source_path is not None:
                zipf = zipfile.ZipFile(zip_source_path)
            else:
                # Type narrowing: if zip_source_path is None, zip_source_bytes cannot be None
                assert zip_source_bytes is not None
                zipf = zipfile.ZipFile(zip_source_bytes)
        except zipfile.BadZipFile as exc:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid zip archive",
            ) from exc

        with zipf:
            names: list[str] = []
            for info in zipf.infolist():
                if info.is_dir() or not info.filename:
                    continue
                p = PurePosixPath(info.filename)
                if _is_ignored_path(p):
                    continue
                if p.is_absolute() or ".." in p.parts:
                    continue
                names.append(info.filename)
            common_root = _extract_common_root(names)

            found_dirs: set[str] = set()
            results: list[dict[str, Any]] = []
            for info in zipf.infolist():
                if info.is_dir() or not info.filename:
                    continue
                raw_path = PurePosixPath(info.filename)
                if _is_ignored_path(raw_path):
                    continue
                if raw_path.is_absolute() or ".." in raw_path.parts:
                    continue
                if raw_path.name.lower() != "skill.md":
                    continue

                rel_path = _strip_common_root(raw_path, common_root)
                skill_dir = rel_path.parent
                if skill_dir == PurePosixPath("."):
                    relative_dir = "."
                    skill_name: str | None = None
                    requires_name = True
                else:
                    relative_dir = skill_dir.as_posix()
                    skill_name = skill_dir.name
                    requires_name = False

                if relative_dir in found_dirs:
                    continue
                found_dirs.add(relative_dir)
                results.append(
                    {
                        "relative_path": relative_dir,
                        "skill_name": skill_name,
                        "requires_name": requires_name,
                    }
                )

            return results

    @staticmethod
    def _download_github_zip(*, github_url: str, destination: Path) -> None:
        parsed = urllib.parse.urlparse(github_url)
        if parsed.scheme not in {"http", "https"}:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid GitHub URL",
            )
        if parsed.netloc.lower() != "github.com":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Only github.com is supported",
            )

        path = parsed.path.strip("/")
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid GitHub repository URL",
            )
        owner = segments[0]
        repo = segments[1].removesuffix(".git")

        # If the user provides a direct zip URL, use it as-is.
        if parsed.path.endswith(".zip") and "/archive/" in parsed.path:
            download_url = github_url
            SkillImportService._download_with_limit(download_url, destination)
            return

        branch: str | None = None
        if len(segments) >= 4 and segments[2] in {"tree", "blob"}:
            # NOTE: This only supports branches without slashes.
            branch = segments[3]

        candidates = [branch] if branch else ["main", "master"]
        last_error: Exception | None = None
        for b in candidates:
            if not b:
                continue
            download_url = (
                f"https://github.com/{owner}/{repo}/archive/refs/heads/{b}.zip"
            )
            try:
                SkillImportService._download_with_limit(download_url, destination)
                return
            except Exception as exc:
                last_error = exc
                continue

        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Failed to download GitHub archive: {last_error}",
        )

    @staticmethod
    def _download_with_limit(url: str, destination: Path) -> None:
        max_size_bytes = get_settings().max_upload_size_mb * 1024 * 1024
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "poco-agent-skill-import/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                length = resp.headers.get("Content-Length")
                if length:
                    try:
                        if int(length) > max_size_bytes:
                            raise AppException(
                                error_code=ErrorCode.BAD_REQUEST,
                                message=f"GitHub archive too large. Max {get_settings().max_upload_size_mb}MB.",
                                details={
                                    "max_bytes": max_size_bytes,
                                    "content_length": int(length),
                                },
                            )
                    except ValueError:
                        pass

                destination.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with destination.open("wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > max_size_bytes:
                            raise AppException(
                                error_code=ErrorCode.BAD_REQUEST,
                                message=f"GitHub archive too large. Max {get_settings().max_upload_size_mb}MB.",
                                details={
                                    "max_bytes": max_size_bytes,
                                    "downloaded_bytes": written,
                                },
                            )
                        f.write(chunk)
        except AppException:
            raise
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Failed to download GitHub archive: {exc}",
            ) from exc

    def _import_one(
        self,
        *,
        db: Session,
        user_id: str,
        zipf: zipfile.ZipFile,
        candidate_by_path: dict[str, dict[str, Any]],
        candidate_dirs: list[PurePosixPath],
        relative_path: str,
        name_override: str | None,
        archive_key: str,
    ) -> SkillImportResultItem:
        candidate = candidate_by_path.get(relative_path)
        if candidate is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Unknown candidate path: {relative_path}",
            )

        requires_name = bool(candidate.get("requires_name"))
        parsed_name = candidate.get("skill_name")
        if requires_name:
            if not name_override or not name_override.strip():
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"name_override is required for {relative_path}",
                )
            skill_name = _validate_skill_name(name_override)
        else:
            skill_name = _validate_skill_name(str(parsed_name or ""))
            if (
                name_override
                and name_override.strip()
                and name_override.strip() != skill_name
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"name_override is not allowed for {relative_path}",
                )

        selection_path = _safe_relative_path(relative_path)

        # Exclude nested candidates under the current selection to avoid mixing multiple skills.
        nested_candidate_dirs: list[PurePosixPath] = []
        for cdir in candidate_dirs:
            if cdir == selection_path:
                continue
            if selection_path == PurePosixPath("."):
                nested_candidate_dirs.append(cdir)
                continue
            if (
                len(cdir.parts) >= len(selection_path.parts)
                and cdir.parts[: len(selection_path.parts)] == selection_path.parts
            ):
                nested_candidate_dirs.append(cdir)

        version_id = str(uuid.uuid4())
        prefix = f"skills/{user_id}/{skill_name}/{version_id}/"

        uploaded = self._upload_skill_from_zip(
            zipf=zipf,
            selection_dir=selection_path,
            exclude_dirs=nested_candidate_dirs,
            destination_prefix=prefix,
        )
        if uploaded == 0:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"No files found under {relative_path}",
            )

        source: dict[str, Any] = {
            "archive_key": archive_key,
            "relative_path": relative_path,
        }
        entry = {
            "s3_key": prefix,
            "is_prefix": True,
            "source": source,
        }

        existing = SkillRepository.get_by_name(db, skill_name, user_id)
        overwritten = existing is not None
        if existing is None:
            skill = Skill(
                name=skill_name,
                scope="user",
                owner_user_id=user_id,
                entry=entry,
            )
            SkillRepository.create(db, skill)
            db.flush()
        else:
            skill = existing
            skill.entry = entry

        install = UserSkillInstallRepository.get_by_user_and_skill(
            db, user_id, skill.id
        )
        if install is None:
            install = UserSkillInstall(user_id=user_id, skill_id=skill.id, enabled=True)
            UserSkillInstallRepository.create(db, install)

        db.commit()
        db.refresh(skill)
        db.refresh(install)

        return SkillImportResultItem(
            relative_path=relative_path,
            skill_name=skill_name,
            skill_id=skill.id,
            overwritten=overwritten,
            status="success",
        )

    def _upload_skill_from_zip(
        self,
        *,
        zipf: zipfile.ZipFile,
        selection_dir: PurePosixPath,
        exclude_dirs: list[PurePosixPath],
        destination_prefix: str,
    ) -> int:
        infos = [
            info for info in zipf.infolist() if info.filename and not info.is_dir()
        ]
        common_root_names: list[str] = []
        for info in infos:
            p = PurePosixPath(info.filename)
            if _is_ignored_path(p):
                continue
            if p.is_absolute() or ".." in p.parts:
                continue
            common_root_names.append(info.filename)
        common_root = _extract_common_root(common_root_names)

        uploaded = 0
        total_uncompressed = 0
        for info in infos:
            raw_path = PurePosixPath(info.filename)
            if raw_path.is_absolute() or ".." in raw_path.parts:
                continue
            if _is_ignored_path(raw_path):
                continue
            rel_path = _strip_common_root(raw_path, common_root)
            if rel_path == PurePosixPath("."):
                continue

            # Check inclusion
            if selection_dir != PurePosixPath("."):
                if len(rel_path.parts) < len(selection_dir.parts):
                    continue
                if rel_path.parts[: len(selection_dir.parts)] != selection_dir.parts:
                    continue

            # Exclude nested candidate skill directories to avoid mixing.
            excluded = False
            for ex in exclude_dirs:
                if ex == PurePosixPath("."):
                    # Root exclusion excludes everything.
                    excluded = True
                    break
                if (
                    len(rel_path.parts) >= len(ex.parts)
                    and rel_path.parts[: len(ex.parts)] == ex.parts
                ):
                    excluded = True
                    break
            if excluded:
                continue

            if selection_dir == PurePosixPath("."):
                relative_in_skill = rel_path
            else:
                try:
                    relative_in_skill = rel_path.relative_to(selection_dir)
                except Exception:
                    continue
            if relative_in_skill.is_absolute() or ".." in relative_in_skill.parts:
                continue

            key = f"{destination_prefix}{relative_in_skill.as_posix()}"
            content_type, _ = mimetypes.guess_type(relative_in_skill.name)

            total_uncompressed += int(getattr(info, "file_size", 0) or 0)
            if total_uncompressed > _MAX_UNCOMPRESSED_BYTES_PER_SKILL:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Skill archive is too large after extraction",
                    details={
                        "max_uncompressed_bytes": _MAX_UNCOMPRESSED_BYTES_PER_SKILL,
                        "total_uncompressed_bytes": total_uncompressed,
                    },
                )
            if uploaded >= _MAX_FILES_PER_SKILL:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Skill archive contains too many files",
                    details={"max_files": _MAX_FILES_PER_SKILL},
                )

            with zipf.open(info, "r") as f:
                self.storage_service.upload_fileobj(
                    fileobj=f, key=key, content_type=content_type
                )
            uploaded += 1

        return uploaded
