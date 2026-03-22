import re
import uuid
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.models.pending_skill_creation import PendingSkillCreation
from app.repositories.pending_skill_creation_repository import (
    PendingSkillCreationRepository,
)
from app.repositories.skill_repository import SkillRepository
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas.pending_skill_creation import (
    PendingSkillCreationConfirmRequest,
    PendingSkillCreationResponse,
)
from app.services.skill_workspace_service import SkillWorkspaceService
from app.services.storage_service import S3StorageService
from app.utils.markdown_front_matter import parse_yaml_front_matter
from app.utils.workspace_manifest import extract_manifest_files, normalize_manifest_path

_SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_ALLOWED_HIDDEN_SKILL_ROOTS = frozenset({".config", ".config_data"})
_PENDING_STATUSES = {"pending", "failed", "creating"}


class PendingSkillCreationService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service
        self.skill_workspace_service = SkillWorkspaceService(
            storage_service=storage_service
        )

    def detect_and_create_pending(
        self,
        db: Session,
        *,
        session: AgentSession,
    ) -> list[PendingSkillCreation]:
        if (
            (session.workspace_export_status or "").strip().lower() != "ready"
            or not session.workspace_manifest_key
            or not session.workspace_files_prefix
        ):
            return []

        skill_tool_executions = ToolExecutionRepository.list_by_session_and_tool_name(
            db,
            session_id=session.id,
            tool_name="Skill",
        )
        successful_skill_tool_executions = [
            execution
            for execution in skill_tool_executions
            if not execution.is_error and execution.tool_output is not None
        ]
        if not successful_skill_tool_executions:
            return []

        visible_skill_names = {
            skill.name
            for skill in SkillRepository.list_visible(db, user_id=session.user_id)
        }
        manifest = self._storage_service().get_manifest(session.workspace_manifest_key)
        created: list[PendingSkillCreation] = []

        for candidate in self._collect_workspace_skill_candidates(
            manifest=manifest,
            workspace_files_prefix=session.workspace_files_prefix,
        ):
            if candidate.detected_name in visible_skill_names:
                continue

            existing = (
                PendingSkillCreationRepository.get_by_session_and_skill_relative_path(
                    db,
                    session_id=session.id,
                    skill_relative_path=candidate.skill_relative_path,
                )
            )
            if existing is not None:
                created.append(existing)
                continue

            pending = PendingSkillCreation(
                user_id=session.user_id,
                session_id=session.id,
                tool_use_id=self._match_tool_use_id(
                    successful_skill_tool_executions,
                    detected_name=candidate.detected_name,
                ),
                detected_name=candidate.detected_name,
                description=candidate.description,
                workspace_files_prefix=session.workspace_files_prefix,
                skill_relative_path=candidate.skill_relative_path,
                status="pending",
            )
            PendingSkillCreationRepository.create(db, pending)
            db.flush()
            created.append(pending)

        return created

    def list_pending_for_user(
        self,
        db: Session,
        *,
        user_id: str,
        session_id: uuid.UUID | None = None,
    ) -> list[PendingSkillCreationResponse]:
        items = PendingSkillCreationRepository.list_by_user(
            db,
            user_id=user_id,
            session_id=session_id,
            statuses=sorted(_PENDING_STATUSES),
        )
        return [self._to_response(item) for item in items]

    def submit_from_workspace(
        self,
        db: Session,
        *,
        user_id: str,
        session: AgentSession,
        folder_path: str,
        skill_name: str | None = None,
        workspace_files_prefix: str | None = None,
    ) -> PendingSkillCreation:
        info = self.skill_workspace_service.inspect_workspace_skill(
            session=session,
            folder_path=folder_path,
            skill_name=skill_name,
            workspace_files_prefix=workspace_files_prefix,
        )
        existing = PendingSkillCreationRepository.find_by_session_and_path(
            db,
            session_id=session.id,
            skill_relative_path=info.folder_path,
        )
        if existing is not None:
            existing.detected_name = info.detected_name
            existing.description = info.description
            existing.workspace_files_prefix = (
                workspace_files_prefix or session.workspace_files_prefix
            )
            if existing.status != "creating":
                existing.status = "pending"
                existing.resolved_name = None
                existing.skill_id = None
                existing.error = None
                existing.result = None
            db.flush()
            return existing

        pending = PendingSkillCreation(
            user_id=user_id,
            session_id=session.id,
            detected_name=info.detected_name,
            description=info.description,
            workspace_files_prefix=workspace_files_prefix
            or session.workspace_files_prefix,
            skill_relative_path=info.folder_path,
            status="pending",
        )
        PendingSkillCreationRepository.create(db, pending)
        db.flush()
        return pending

    def get_creation(
        self,
        db: Session,
        *,
        user_id: str,
        creation_id: uuid.UUID,
    ) -> PendingSkillCreationResponse:
        item = self._get_owned_creation(db, user_id=user_id, creation_id=creation_id)
        return self._to_response(item)

    def confirm(
        self,
        db: Session,
        *,
        user_id: str,
        creation_id: uuid.UUID,
        request: PendingSkillCreationConfirmRequest,
    ) -> PendingSkillCreationResponse:
        pending = self._get_owned_creation(db, user_id=user_id, creation_id=creation_id)
        if pending.status not in {"pending", "failed"}:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Pending skill creation cannot be confirmed from status: {pending.status}",
            )

        final_name = self._validate_skill_name(
            request.resolved_name or pending.detected_name
        )
        existing_skill = SkillRepository.get_by_name(db, final_name, user_id)
        if existing_skill is not None and not request.overwrite:
            raise AppException(
                error_code=ErrorCode.SKILL_ALREADY_EXISTS,
                message=f"Skill already exists: {final_name}",
            )

        pending.status = "creating"
        pending.error = None
        pending.resolved_name = final_name
        db.flush()

        try:
            session = self._get_session_for_pending(db, pending)
            result = self.skill_workspace_service.create_skill_from_workspace(
                db,
                user_id=user_id,
                session=session,
                folder_path=pending.skill_relative_path,
                skill_name=final_name,
                description=request.description,
                overwrite=request.overwrite,
                pending_creation_id=pending.id,
                workspace_files_prefix=pending.workspace_files_prefix,
            )
            pending.status = "success"
            pending.skill_id = result.skill_id
            pending.error = None
            pending.result = {
                "skill_id": result.skill_id,
                "skill_name": result.name,
                "overwritten": result.overwritten,
            }
            pending.description = result.description
            db.commit()
            db.refresh(pending)
            return self._to_response(pending)
        except Exception as exc:
            pending.status = "failed"
            pending.error = str(exc)
            db.commit()
            raise

    def cancel(
        self,
        db: Session,
        *,
        user_id: str,
        creation_id: uuid.UUID,
        reason: str | None = None,
    ) -> PendingSkillCreationResponse:
        pending = self._get_owned_creation(db, user_id=user_id, creation_id=creation_id)
        if pending.status == "success":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Cannot cancel a completed skill creation",
            )
        pending.status = "canceled"
        pending.error = (
            reason.strip()[:1000]
            if isinstance(reason, str) and reason.strip()
            else None
        )
        db.commit()
        db.refresh(pending)
        return self._to_response(pending)

    def _get_owned_creation(
        self,
        db: Session,
        *,
        user_id: str,
        creation_id: uuid.UUID,
    ) -> PendingSkillCreation:
        item = PendingSkillCreationRepository.get_by_id(db, creation_id)
        if item is None or item.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Pending skill creation not found: {creation_id}",
            )
        return item

    def _extract_description_from_key(self, key: str) -> str | None:
        content = self._storage_service().get_text(key)
        frontmatter = parse_yaml_front_matter(content)
        description = frontmatter.get("description")
        if not isinstance(description, str):
            return None
        normalized = description.strip()
        return normalized[:1000] if normalized else None

    @staticmethod
    def _get_session_for_pending(
        db: Session,
        pending: PendingSkillCreation,
    ) -> AgentSession:
        session = (
            db.query(AgentSession).filter(AgentSession.id == pending.session_id).first()
        )
        if session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {pending.session_id}",
            )
        return session

    @staticmethod
    def _match_tool_use_id(
        tool_executions: list,
        *,
        detected_name: str,
    ) -> str | None:
        clean_name = detected_name.strip().lower()
        for execution in tool_executions:
            tool_input = (
                execution.tool_input if isinstance(execution.tool_input, dict) else {}
            )
            for value in tool_input.values():
                if isinstance(value, str) and clean_name in value.lower():
                    return execution.tool_use_id
        return tool_executions[0].tool_use_id if len(tool_executions) == 1 else None

    def _collect_workspace_skill_candidates(
        self,
        *,
        manifest: object,
        workspace_files_prefix: str,
    ) -> list["_DetectedWorkspaceSkill"]:
        files = extract_manifest_files(manifest)
        candidates: list[_DetectedWorkspaceSkill] = []
        # Deduplicate by skill name because workspace exports may include both
        # .config/skills/<name>/ (symlink) and .config_data/skills/<name>/ (real path).
        seen_names: set[str] = set()

        for item in files:
            normalized_path = normalize_manifest_path(item.get("path"))
            if not normalized_path or not normalized_path.endswith("/SKILL.md"):
                continue
            parent = PurePosixPath(normalized_path).parent
            parent_str = parent.as_posix()

            parts = [part for part in parent.parts if part]
            if len(parts) != 3 or parts[1] != "skills":
                continue
            if parts[0] not in _ALLOWED_HIDDEN_SKILL_ROOTS:
                continue

            detected_name = parts[2]
            if detected_name in seen_names:
                continue
            if not self._looks_like_valid_skill_name(detected_name):
                continue

            object_key = (
                item.get("key")
                or item.get("object_key")
                or item.get("oss_key")
                or item.get("s3_key")
            )
            if not isinstance(object_key, str) or not object_key.strip():
                object_key = f"{workspace_files_prefix.rstrip('/')}/{normalized_path.lstrip('/')}"

            candidates.append(
                _DetectedWorkspaceSkill(
                    detected_name=detected_name,
                    description=self._extract_description_from_key(object_key),
                    skill_relative_path=parent_str,
                )
            )
            seen_names.add(detected_name)

        return candidates

    def _storage_service(self) -> S3StorageService:
        if self.storage_service is None:
            self.storage_service = S3StorageService()
        return self.storage_service

    @staticmethod
    def _looks_like_valid_skill_name(name: str) -> bool:
        return (
            bool(name)
            and name not in {".", ".."}
            and bool(_SKILL_NAME_PATTERN.fullmatch(name))
        )

    @staticmethod
    def _validate_skill_name(name: str) -> str:
        value = (name or "").strip()
        if not PendingSkillCreationService._looks_like_valid_skill_name(value):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid skill name: {name}",
            )
        return value

    @staticmethod
    def _to_response(
        pending: PendingSkillCreation,
    ) -> PendingSkillCreationResponse:
        return PendingSkillCreationResponse(
            id=pending.id,
            session_id=pending.session_id,
            tool_use_id=pending.tool_use_id,
            detected_name=pending.detected_name,
            resolved_name=pending.resolved_name,
            description=pending.description,
            workspace_files_prefix=pending.workspace_files_prefix,
            skill_relative_path=pending.skill_relative_path,
            status=pending.status,
            skill_id=pending.skill_id,
            error=pending.error,
            result=pending.result,
            created_at=pending.created_at,
            updated_at=pending.updated_at,
        )


class _DetectedWorkspaceSkill:
    def __init__(
        self,
        *,
        detected_name: str,
        description: str | None,
        skill_relative_path: str,
    ) -> None:
        self.detected_name = detected_name
        self.description = description
        self.skill_relative_path = skill_relative_path
