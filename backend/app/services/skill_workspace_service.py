import re
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.models.skill import Skill
from app.models.user_skill_install import UserSkillInstall
from app.repositories.skill_repository import SkillRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.services.storage_service import S3StorageService
from app.utils.markdown_front_matter import (
    parse_yaml_front_matter,
    update_yaml_front_matter,
)
from app.utils.workspace_manifest import (
    extract_manifest_files,
    normalize_manifest_path,
)

_SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class WorkspaceSkillInfo(BaseModel):
    folder_path: str
    detected_name: str
    description: str | None = None


class WorkspaceSkillCreateResult(BaseModel):
    skill_id: int
    name: str
    description: str | None = None
    overwritten: bool


class SkillWorkspaceService:
    """Shared service for creating skills from exported workspace files."""

    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service

    def inspect_workspace_skill(
        self,
        *,
        session: AgentSession,
        folder_path: str,
        skill_name: str | None = None,
        workspace_files_prefix: str | None = None,
    ) -> WorkspaceSkillInfo:
        normalized_folder_path = self._normalize_folder_path(folder_path)
        skill_markdown_key = self._resolve_skill_markdown_key(
            session=session,
            folder_path=normalized_folder_path,
            workspace_files_prefix=workspace_files_prefix,
        )
        frontmatter = parse_yaml_front_matter(
            self._storage_service().get_text(skill_markdown_key)
        )
        description = self._normalize_description(frontmatter.get("description"))
        detected_name = self._validate_skill_name(
            skill_name
            or self._normalize_name(frontmatter.get("name"))
            or normalized_folder_path.rsplit("/", 1)[-1]
        )
        return WorkspaceSkillInfo(
            folder_path=normalized_folder_path,
            detected_name=detected_name,
            description=description,
        )

    def create_skill_from_workspace(
        self,
        db: Session,
        *,
        user_id: str,
        session: AgentSession,
        folder_path: str,
        skill_name: str | None = None,
        description: str | None = None,
        overwrite: bool = False,
        pending_creation_id: uuid.UUID | None = None,
        workspace_files_prefix: str | None = None,
    ) -> WorkspaceSkillCreateResult:
        info = self.inspect_workspace_skill(
            session=session,
            folder_path=folder_path,
            skill_name=skill_name,
            workspace_files_prefix=workspace_files_prefix,
        )
        if description is not None:
            info.description = self._normalize_description(description)
        existing_skill = SkillRepository.get_by_name(db, info.detected_name, user_id)
        if existing_skill is not None and not overwrite:
            raise AppException(
                error_code=ErrorCode.SKILL_ALREADY_EXISTS,
                message=f"Skill already exists: {info.detected_name}",
            )

        workspace_prefix = self._resolve_workspace_files_prefix(
            session=session,
            workspace_files_prefix=workspace_files_prefix,
        )
        source_prefix = f"{workspace_prefix}/{info.folder_path.lstrip('/')}"
        version_id = str(uuid.uuid4())
        destination_prefix = f"skills/{user_id}/{info.detected_name}/{version_id}"
        copied = self._storage_service().copy_prefix(
            source_prefix=source_prefix,
            destination_prefix=destination_prefix,
        )
        if copied == 0:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="No skill files found to create",
            )
        self._rewrite_skill_markdown(
            destination_prefix=destination_prefix,
            skill_name=info.detected_name,
            description=info.description,
        )

        source: dict[str, str] = {
            "kind": "skill-creator",
            "session_id": str(session.id),
        }
        if pending_creation_id is not None:
            source["pending_creation_id"] = str(pending_creation_id)
        entry = {
            "s3_key": f"{destination_prefix}/",
            "is_prefix": True,
        }

        overwritten = existing_skill is not None
        if existing_skill is None:
            skill = Skill(
                name=info.detected_name,
                description=info.description,
                scope="user",
                owner_user_id=user_id,
                entry=entry,
                source=source,
            )
            SkillRepository.create(db, skill)
            db.flush()
        else:
            skill = existing_skill
            skill.name = info.detected_name
            skill.description = info.description
            skill.entry = entry
            skill.source = source
            db.flush()

        install = UserSkillInstallRepository.get_by_user_and_skill(
            db,
            user_id,
            skill.id,
        )
        if install is None:
            UserSkillInstallRepository.create(
                db,
                UserSkillInstall(user_id=user_id, skill_id=skill.id, enabled=True),
            )
        else:
            install.enabled = True

        return WorkspaceSkillCreateResult(
            skill_id=skill.id,
            name=skill.name,
            description=skill.description,
            overwritten=overwritten,
        )

    def _resolve_skill_markdown_key(
        self,
        *,
        session: AgentSession,
        folder_path: str,
        workspace_files_prefix: str | None = None,
    ) -> str:
        skill_markdown_path = f"{folder_path}/SKILL.md"
        workspace_prefix = self._resolve_workspace_files_prefix(
            session=session,
            workspace_files_prefix=workspace_files_prefix,
        )
        fallback_key = f"{workspace_prefix}/{skill_markdown_path.lstrip('/')}"
        if self._storage_service().exists(fallback_key):
            return fallback_key

        self._require_workspace_export_ready(session)
        manifest_key = (session.workspace_manifest_key or "").strip()
        if not manifest_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace manifest is not available",
            )

        manifest = self._storage_service().get_manifest(manifest_key)
        for file_entry in extract_manifest_files(manifest):
            normalized_path = normalize_manifest_path(file_entry.get("path"))
            if normalized_path != skill_markdown_path:
                continue
            object_key = self._extract_object_key(file_entry)
            if object_key:
                return object_key

        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message="Generated skill files are not available in workspace export",
        )

    def _require_workspace_export_ready(self, session: AgentSession) -> None:
        if (session.workspace_export_status or "").strip().lower() != "ready":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace export not ready",
            )

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
    def _validate_skill_name(name: str) -> str:
        value = (name or "").strip()
        if (
            not value
            or value in {".", ".."}
            or _SKILL_NAME_PATTERN.fullmatch(value) is None
        ):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid skill name: {name}",
            )
        return value

    @staticmethod
    def _normalize_name(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_description(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized[:1000] if normalized else None

    @staticmethod
    def _extract_object_key(file_entry: dict) -> str | None:
        for key in ("key", "object_key", "oss_key", "s3_key"):
            value = file_entry.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    @staticmethod
    def _resolve_workspace_files_prefix(
        *,
        session: AgentSession,
        workspace_files_prefix: str | None = None,
    ) -> str:
        workspace_prefix = (
            (workspace_files_prefix or session.workspace_files_prefix or "")
            .strip()
            .rstrip("/")
        )
        if not workspace_prefix:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace files prefix is missing",
            )
        return workspace_prefix

    def _storage_service(self) -> S3StorageService:
        if self.storage_service is None:
            self.storage_service = S3StorageService()
        return self.storage_service

    def _rewrite_skill_markdown(
        self,
        *,
        destination_prefix: str,
        skill_name: str,
        description: str | None,
    ) -> None:
        skill_markdown_key = f"{destination_prefix}/SKILL.md"
        storage_service = self._storage_service()
        markdown = storage_service.get_text(skill_markdown_key)
        updated_markdown = update_yaml_front_matter(
            markdown,
            {
                "name": skill_name,
                "description": description,
            },
        )
        storage_service.put_object(
            key=skill_markdown_key,
            body=updated_markdown.encode("utf-8"),
            content_type="text/markdown; charset=utf-8",
        )
