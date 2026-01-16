from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.skill_preset import SkillPreset
from app.repositories.skill_preset_repository import SkillPresetRepository
from app.schemas.skill_preset import (
    SkillPresetCreateRequest,
    SkillPresetResponse,
    SkillPresetUpdateRequest,
)


class SkillPresetService:
    def list_presets(
        self, db: Session, user_id: str, include_inactive: bool = False
    ) -> list[SkillPresetResponse]:
        presets = SkillPresetRepository.list_visible(
            db, user_id=user_id, include_inactive=include_inactive
        )
        return [self._to_response(p) for p in presets]

    def get_preset(
        self, db: Session, user_id: str, preset_id: int
    ) -> SkillPresetResponse:
        preset = SkillPresetRepository.get_by_id(db, preset_id)
        if not preset or (
            preset.source != "system" and preset.owner_user_id != user_id
        ):
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_NOT_FOUND,
                message=f"Skill preset not found: {preset_id}",
            )
        return self._to_response(preset)

    def create_preset(
        self, db: Session, user_id: str, request: SkillPresetCreateRequest
    ) -> SkillPresetResponse:
        if SkillPresetRepository.get_by_name(db, request.name):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Skill preset already exists: {request.name}",
            )

        preset = SkillPreset(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            category=request.category,
            entry=request.entry,
            default_config=request.default_config,
            config_schema=request.config_schema,
            source="user",
            owner_user_id=user_id,
            version=request.version,
            is_active=True,
        )

        SkillPresetRepository.create(db, preset)
        db.commit()
        db.refresh(preset)
        return self._to_response(preset)

    def update_preset(
        self,
        db: Session,
        user_id: str,
        preset_id: int,
        request: SkillPresetUpdateRequest,
    ) -> SkillPresetResponse:
        preset = SkillPresetRepository.get_by_id(db, preset_id)
        if not preset:
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_NOT_FOUND,
                message=f"Skill preset not found: {preset_id}",
            )
        if preset.source == "system":
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_CREATE_FORBIDDEN,
                message="Cannot modify system skill presets",
            )
        if preset.owner_user_id and preset.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Skill preset does not belong to the user",
            )

        if request.display_name is not None:
            preset.display_name = request.display_name
        if request.description is not None:
            preset.description = request.description
        if request.category is not None:
            preset.category = request.category
        if request.entry is not None:
            preset.entry = request.entry
        if request.default_config is not None:
            preset.default_config = request.default_config
        if request.config_schema is not None:
            preset.config_schema = request.config_schema
        if request.version is not None:
            preset.version = request.version
        if request.is_active is not None:
            preset.is_active = request.is_active

        db.commit()
        db.refresh(preset)
        return self._to_response(preset)

    def delete_preset(self, db: Session, user_id: str, preset_id: int) -> None:
        preset = SkillPresetRepository.get_by_id(db, preset_id)
        if not preset:
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_NOT_FOUND,
                message=f"Skill preset not found: {preset_id}",
            )
        if preset.source == "system":
            raise AppException(
                error_code=ErrorCode.SKILL_PRESET_CREATE_FORBIDDEN,
                message="Cannot delete system skill presets",
            )
        if preset.owner_user_id and preset.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Skill preset does not belong to the user",
            )

        SkillPresetRepository.delete(db, preset)
        db.commit()

    @staticmethod
    def _to_response(preset: SkillPreset) -> SkillPresetResponse:
        return SkillPresetResponse(
            id=preset.id,
            name=preset.name,
            display_name=preset.display_name,
            description=preset.description,
            category=preset.category,
            entry=preset.entry,
            default_config=preset.default_config,
            config_schema=preset.config_schema,
            source=preset.source,
            owner_user_id=preset.owner_user_id,
            version=preset.version,
            is_active=preset.is_active,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
        )
