import mimetypes
import re
import uuid
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.skill import Skill
from app.repositories.skill_repository import SkillRepository
from app.schemas.source import SourceInfo
from app.schemas.skill import (
    SkillCreateRequest,
    SkillResponse,
    SkillUpdateRequest,
)
from app.schemas.workspace import FileNode
from app.schemas.execution_settings import SkillManifestValidationResponse
from app.services.storage_service import S3StorageService
from app.services.source_utils import infer_capability_source
from app.utils.markdown_front_matter import update_yaml_front_matter
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_file_entries,
    normalize_manifest_path,
)


_SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_skill_name(name: str) -> str:
    value = (name or "").strip()
    if not value or value in {".", ".."} or not _SKILL_NAME_PATTERN.fullmatch(value):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid skill name: {name}",
        )
    return value


class SkillService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service

    def list_skills(self, db: Session, user_id: str) -> list[SkillResponse]:
        skills = SkillRepository.list_visible(db, user_id=user_id)
        return [self._to_response(s) for s in skills]

    def get_skill(self, db: Session, user_id: str, skill_id: int) -> SkillResponse:
        skill = self._get_visible_skill(db, user_id, skill_id)
        return self._to_response(skill)

    def list_skill_files(
        self,
        db: Session,
        user_id: str,
        skill_id: int,
    ) -> list[FileNode]:
        skill = self._get_visible_skill(db, user_id, skill_id)
        entry = skill.entry if isinstance(skill.entry, dict) else {}
        raw_key = entry.get("s3_key")
        if not isinstance(raw_key, str) or not raw_key.strip():
            return []

        s3_key = raw_key.strip()
        if self._is_prefix_entry(entry, s3_key):
            return self._build_file_nodes_from_prefix(s3_key)
        return self._build_file_nodes_from_object(s3_key)

    def create_skill(
        self, db: Session, user_id: str, request: SkillCreateRequest
    ) -> SkillResponse:
        name = _validate_skill_name(request.name)
        scope = (request.scope or "user").strip() or "user"

        if SkillRepository.get_by_name(db, name, user_id):
            raise AppException(
                error_code=ErrorCode.SKILL_ALREADY_EXISTS,
                message=f"Skill already exists: {name}",
            )

        skill = Skill(
            name=name,
            description=request.description.strip() or None
            if request.description is not None
            else None,
            scope=scope,
            owner_user_id=user_id,
            entry=request.entry or {},
            source={"kind": "manual"},
            lifecycle_state="active",
        )
        self._apply_manifest_metadata(skill)

        SkillRepository.create(db, skill)
        db.commit()
        db.refresh(skill)
        return self._to_response(skill)

    def update_skill(
        self,
        db: Session,
        user_id: str,
        skill_id: int,
        request: SkillUpdateRequest,
    ) -> SkillResponse:
        skill = SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise AppException(
                error_code=ErrorCode.SKILL_NOT_FOUND,
                message=f"Skill not found: {skill_id}",
            )
        if skill.scope == "system":
            raise AppException(
                error_code=ErrorCode.SKILL_MODIFY_FORBIDDEN,
                message="Cannot modify system skills",
            )
        if skill.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Skill does not belong to the user",
            )

        target_name = skill.name
        if (
            request.name is not None
            and request.name.strip()
            and request.name != skill.name
        ):
            new_name = _validate_skill_name(request.name)
            if SkillRepository.get_by_name(db, new_name, user_id):
                raise AppException(
                    error_code=ErrorCode.SKILL_ALREADY_EXISTS,
                    message=f"Skill already exists: {new_name}",
                )
            target_name = new_name

        target_description = skill.description
        if request.description is not None:
            target_description = request.description.strip() or None

        if request.entry is None:
            versioned_entry = self._version_skill_assets(
                skill=skill,
                user_id=user_id,
                target_name=target_name,
                target_description=target_description,
            )
            if versioned_entry is not None:
                skill.entry = versioned_entry

        skill.name = target_name

        if request.scope is not None and request.scope.strip():
            skill.scope = request.scope.strip()
        if request.description is not None:
            skill.description = target_description
        if request.entry is not None:
            skill.entry = request.entry

        self._apply_manifest_metadata(skill)

        db.commit()
        db.refresh(skill)
        return self._to_response(skill)

    def validate_manifest(
        self, db: Session, user_id: str, skill_id: int
    ) -> SkillManifestValidationResponse:
        skill = self._get_visible_skill(db, user_id, skill_id)
        manifest = self._effective_manifest(skill)
        errors: list[str] = []
        if not isinstance(manifest, dict):
            errors.append("manifest must be an object")
        else:
            if (
                not isinstance(manifest.get("name"), str)
                or not manifest["name"].strip()
            ):
                errors.append("manifest.name is required")
            if not isinstance(manifest.get("entry"), dict):
                errors.append("manifest.entry must be an object")
        return SkillManifestValidationResponse(valid=not errors, errors=errors)

    def delete_skill(self, db: Session, user_id: str, skill_id: int) -> None:
        skill = SkillRepository.get_by_id(db, skill_id)
        if not skill:
            raise AppException(
                error_code=ErrorCode.SKILL_NOT_FOUND,
                message=f"Skill not found: {skill_id}",
            )
        if skill.scope == "system":
            raise AppException(
                error_code=ErrorCode.SKILL_MODIFY_FORBIDDEN,
                message="Cannot delete system skills",
            )
        if skill.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Skill does not belong to the user",
            )

        SkillRepository.delete(db, skill)
        db.commit()

    @staticmethod
    def _get_visible_skill(db: Session, user_id: str, skill_id: int) -> Skill:
        skill = SkillRepository.get_by_id(db, skill_id)
        if not skill or (skill.scope != "system" and skill.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.SKILL_NOT_FOUND,
                message=f"Skill not found: {skill_id}",
            )
        return skill

    @staticmethod
    def _is_prefix_entry(entry: dict[str, Any], s3_key: str) -> bool:
        raw_is_prefix = entry.get("is_prefix")
        if isinstance(raw_is_prefix, bool):
            return raw_is_prefix
        if isinstance(raw_is_prefix, str):
            return raw_is_prefix.strip().lower() in {"1", "true", "yes", "on"}
        return s3_key.endswith("/")

    def _build_file_nodes_from_prefix(self, prefix: str) -> list[FileNode]:
        normalized_prefix = prefix.strip().rstrip("/")
        if not normalized_prefix:
            return []

        storage_service = self._storage_service()
        prefix_with_slash = f"{normalized_prefix}/"
        file_entries: list[dict[str, Any]] = []
        file_url_map: dict[str, str] = {}

        for object_key in storage_service.list_objects(prefix_with_slash):
            if object_key.endswith("/"):
                continue
            relative_path = object_key[len(prefix_with_slash) :].lstrip("/")
            normalized_path = normalize_manifest_path(relative_path)
            if not normalized_path:
                continue

            mime_type, _ = mimetypes.guess_type(relative_path)
            file_entries.append(
                {
                    "path": normalized_path,
                    "key": object_key,
                    "mimeType": mime_type,
                }
            )
            file_url_map[normalized_path] = storage_service.presign_get(
                object_key,
                response_content_disposition="inline",
                response_content_type=mime_type,
            )

        if not file_entries:
            return []

        raw_nodes = build_nodes_from_file_entries(file_entries)
        return build_workspace_file_nodes(
            raw_nodes,
            file_url_builder=lambda file_path: file_url_map.get(
                normalize_manifest_path(file_path) or file_path
            ),
        )

    def _build_file_nodes_from_object(self, key: str) -> list[FileNode]:
        storage_service = self._storage_service()
        if not storage_service.exists(key):
            return []

        filename = PurePosixPath(key).name
        normalized_path = normalize_manifest_path(filename)
        if not normalized_path:
            return []

        mime_type, _ = mimetypes.guess_type(filename)
        raw_nodes = build_nodes_from_file_entries(
            [
                {
                    "path": normalized_path,
                    "key": key,
                    "mimeType": mime_type,
                }
            ]
        )
        file_url_map = {
            normalized_path: storage_service.presign_get(
                key,
                response_content_disposition="inline",
                response_content_type=mime_type,
            )
        }
        return build_workspace_file_nodes(
            raw_nodes,
            file_url_builder=lambda file_path: file_url_map.get(
                normalize_manifest_path(file_path) or file_path
            ),
        )

    def _storage_service(self) -> S3StorageService:
        if self.storage_service is None:
            self.storage_service = S3StorageService()
        return self.storage_service

    def _version_skill_assets(
        self,
        *,
        skill: Skill,
        user_id: str,
        target_name: str,
        target_description: str | None,
    ) -> dict[str, Any] | None:
        if skill.scope == "system" or not isinstance(skill.entry, dict):
            return None

        raw_key = skill.entry.get("s3_key")
        if not isinstance(raw_key, str) or not raw_key.strip():
            return None

        if target_name == skill.name and target_description == skill.description:
            return None

        source_key = raw_key.strip()
        if not self._is_prefix_entry(skill.entry, source_key):
            return None

        source_prefix = source_key.rstrip("/")
        if not source_prefix:
            return None

        destination_prefix = f"skills/{user_id}/{target_name}/{uuid.uuid4()}"
        storage_service = self._storage_service()
        copied = storage_service.copy_prefix(
            source_prefix=source_prefix,
            destination_prefix=destination_prefix,
        )
        if copied == 0:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="No skill files found to version",
            )

        self._rewrite_skill_markdown(
            destination_prefix=destination_prefix,
            skill_name=target_name,
            description=target_description,
        )

        next_entry = dict(skill.entry)
        next_entry["s3_key"] = f"{destination_prefix}/"
        next_entry["is_prefix"] = True
        return next_entry

    def _rewrite_skill_markdown(
        self,
        *,
        destination_prefix: str,
        skill_name: str,
        description: str | None,
    ) -> None:
        skill_markdown_key = f"{destination_prefix.rstrip('/')}/SKILL.md"
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

    @staticmethod
    def _build_entry_checksum(entry: dict[str, Any]) -> str:
        payload = json.dumps(
            entry, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_manifest(skill: Skill) -> dict[str, Any]:
        entry = skill.entry if isinstance(skill.entry, dict) else {}
        return {
            "name": skill.name,
            "description": skill.description,
            "entry": entry,
            "source": skill.source or {},
            "scope": skill.scope,
        }

    @classmethod
    def _apply_manifest_metadata(cls, skill: Skill) -> None:
        entry = skill.entry if isinstance(skill.entry, dict) else {}
        skill.manifest_version = "v1"
        skill.manifest = cls._build_manifest(skill)
        skill.entry_checksum = cls._build_entry_checksum(entry)
        lifecycle_state = getattr(skill, "lifecycle_state", None)
        if not isinstance(lifecycle_state, str) or not lifecycle_state.strip():
            skill.lifecycle_state = "active"

    @classmethod
    def _effective_manifest(cls, skill: Skill) -> dict[str, Any]:
        manifest = getattr(skill, "manifest", None)
        if isinstance(manifest, dict):
            return manifest
        return cls._build_manifest(skill)

    @staticmethod
    def _to_response(skill: Skill) -> SkillResponse:
        source_dict = infer_capability_source(
            scope=skill.scope,
            source=getattr(skill, "source", None),
            entry=skill.entry,
        )
        return SkillResponse(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            entry=skill.entry,
            manifest_version=(
                getattr(skill, "manifest_version", None)
                if isinstance(getattr(skill, "manifest_version", None), str)
                else "v1"
            ),
            manifest=SkillService._effective_manifest(skill),
            entry_checksum=(
                getattr(skill, "entry_checksum", None)
                if isinstance(getattr(skill, "entry_checksum", None), str)
                else SkillService._build_entry_checksum(
                    skill.entry if isinstance(skill.entry, dict) else {}
                )
            ),
            lifecycle_state=str(
                getattr(skill, "lifecycle_state", "active")
                if isinstance(getattr(skill, "lifecycle_state", None), str)
                else "active"
            ),
            source=SourceInfo.model_validate(source_dict),
            scope=skill.scope,
            owner_user_id=skill.owner_user_id,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
        )
