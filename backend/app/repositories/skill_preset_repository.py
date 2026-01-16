from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.skill_preset import SkillPreset


class SkillPresetRepository:
    @staticmethod
    def create(session_db: Session, preset: SkillPreset) -> SkillPreset:
        session_db.add(preset)
        return preset

    @staticmethod
    def get_by_id(session_db: Session, preset_id: int) -> SkillPreset | None:
        return session_db.query(SkillPreset).filter(SkillPreset.id == preset_id).first()

    @staticmethod
    def get_by_name(session_db: Session, name: str) -> SkillPreset | None:
        return session_db.query(SkillPreset).filter(SkillPreset.name == name).first()

    @staticmethod
    def list_all(
        session_db: Session, include_inactive: bool = False
    ) -> list[SkillPreset]:
        query = session_db.query(SkillPreset)
        if not include_inactive:
            query = query.filter(SkillPreset.is_active.is_(True))
        return query.order_by(SkillPreset.created_at.desc()).all()

    @staticmethod
    def list_visible(
        session_db: Session, user_id: str, include_inactive: bool = False
    ) -> list[SkillPreset]:
        query = session_db.query(SkillPreset).filter(
            or_(SkillPreset.source == "system", SkillPreset.owner_user_id == user_id)
        )
        if not include_inactive:
            query = query.filter(SkillPreset.is_active.is_(True))
        return query.order_by(SkillPreset.created_at.desc()).all()

    @staticmethod
    def delete(session_db: Session, preset: SkillPreset) -> None:
        session_db.delete(preset)
