import re

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.skill import Skill
from app.repositories.skill_repository import SkillRepository
from app.schemas.skill import SkillCreateRequest, SkillResponse, SkillUpdateRequest


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
    def list_skills(self, db: Session, user_id: str) -> list[SkillResponse]:
        skills = SkillRepository.list_visible(db, user_id=user_id)
        return [self._to_response(s) for s in skills]

    def get_skill(self, db: Session, user_id: str, skill_id: int) -> SkillResponse:
        skill = SkillRepository.get_by_id(db, skill_id)
        if not skill or (skill.scope != "system" and skill.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.SKILL_NOT_FOUND,
                message=f"Skill not found: {skill_id}",
            )
        return self._to_response(skill)

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
            scope=scope,
            owner_user_id=user_id,
            entry=request.entry or {},
        )

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
            skill.name = new_name

        if request.scope is not None and request.scope.strip():
            skill.scope = request.scope.strip()
        if request.entry is not None:
            skill.entry = request.entry

        db.commit()
        db.refresh(skill)
        return self._to_response(skill)

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
    def _to_response(skill: Skill) -> SkillResponse:
        return SkillResponse(
            id=skill.id,
            name=skill.name,
            entry=skill.entry,
            scope=skill.scope,
            owner_user_id=skill.owner_user_id,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
        )
