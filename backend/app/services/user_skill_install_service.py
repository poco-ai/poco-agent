from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user_skill_install import UserSkillInstall
from app.repositories.skill_repository import SkillRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.user_skill_install import (
    UserSkillInstallBulkUpdateRequest,
    UserSkillInstallBulkUpdateResponse,
    UserSkillInstallCreateRequest,
    UserSkillInstallResponse,
    UserSkillInstallUpdateRequest,
)


class UserSkillInstallService:
    def list_installs(
        self, db: Session, user_id: str
    ) -> list[UserSkillInstallResponse]:
        installs = UserSkillInstallRepository.list_by_user(db, user_id)
        return [self._to_response(i) for i in installs]

    def create_install(
        self, db: Session, user_id: str, request: UserSkillInstallCreateRequest
    ) -> UserSkillInstallResponse:
        skill = SkillRepository.get_by_id(db, request.skill_id)
        if not skill or (skill.scope != "system" and skill.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.SKILL_NOT_FOUND,
                message=f"Skill not found: {request.skill_id}",
            )
        existing = UserSkillInstallRepository.get_by_user_and_skill(
            db, user_id, request.skill_id
        )
        if existing:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Skill install already exists for skill",
            )

        install = UserSkillInstall(
            user_id=user_id,
            skill_id=request.skill_id,
            enabled=(
                bool(skill.force_enabled) or request.enabled
                if request.enabled is not None
                else bool(skill.default_enabled or skill.force_enabled)
            ),
        )
        UserSkillInstallRepository.create(db, install)
        db.commit()
        db.refresh(install)

        return self._to_response(install)

    def update_install(
        self,
        db: Session,
        user_id: str,
        install_id: int,
        request: UserSkillInstallUpdateRequest,
    ) -> UserSkillInstallResponse:
        install = UserSkillInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Skill install not found: {install_id}",
            )

        if request.enabled is not None:
            skill = SkillRepository.get_by_id(db, install.skill_id)
            if (
                skill
                and skill.scope == "system"
                and skill.force_enabled
                and not request.enabled
            ):
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system skills",
                )
            install.enabled = request.enabled

        db.commit()
        db.refresh(install)
        return self._to_response(install)

    def bulk_update_installs(
        self,
        db: Session,
        user_id: str,
        request: UserSkillInstallBulkUpdateRequest,
    ) -> UserSkillInstallBulkUpdateResponse:
        if request.enabled is False:
            installs = UserSkillInstallRepository.list_by_user(db, user_id)
            target_ids = set(
                request.install_ids or [install.id for install in installs]
            )
            forced_install_ids = {
                install.id
                for install in installs
                if install.id in target_ids
                and (
                    (skill := SkillRepository.get_by_id(db, install.skill_id))
                    is not None
                    and skill.scope == "system"
                    and skill.force_enabled
                )
            }
            if forced_install_ids:
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system skills",
                )
        updated_count = UserSkillInstallRepository.bulk_set_enabled(
            db,
            user_id=user_id,
            enabled=request.enabled,
            install_ids=request.install_ids,
        )
        db.commit()
        return UserSkillInstallBulkUpdateResponse(updated_count=updated_count)

    def delete_install(self, db: Session, user_id: str, install_id: int) -> None:
        install = UserSkillInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Skill install not found: {install_id}",
            )
        UserSkillInstallRepository.delete(db, install)
        db.commit()

    @staticmethod
    def _to_response(install: UserSkillInstall) -> UserSkillInstallResponse:
        return UserSkillInstallResponse(
            id=install.id,
            user_id=install.user_id,
            skill_id=install.skill_id,
            enabled=install.enabled,
            created_at=install.created_at,
            updated_at=install.updated_at,
        )
