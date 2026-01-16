from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user_skill_install import UserSkillInstall
from app.repositories.skill_preset_repository import SkillPresetRepository
from app.repositories.user_skill_install_repository import UserSkillInstallRepository
from app.schemas.user_skill_install import (
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
        preset = SkillPresetRepository.get_by_id(db, request.preset_id)
        if not preset or (
            preset.source != "system" and preset.owner_user_id != user_id
        ):
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_NOT_FOUND,
                message=f"Skill preset not found: {request.preset_id}",
            )
        if not preset.is_active:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Skill preset is inactive",
            )

        install = UserSkillInstall(
            user_id=user_id,
            preset_id=request.preset_id,
            enabled=request.enabled,
            overrides=request.overrides,
        )
        try:
            UserSkillInstallRepository.create(db, install)
            db.commit()
            db.refresh(install)
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Skill install already exists for preset",
            ) from exc

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
            install.enabled = request.enabled
        if request.overrides is not None:
            install.overrides = request.overrides

        db.commit()
        db.refresh(install)
        return self._to_response(install)

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
            preset_id=install.preset_id,
            enabled=install.enabled,
            overrides=install.overrides,
            created_at=install.created_at,
            updated_at=install.updated_at,
        )
