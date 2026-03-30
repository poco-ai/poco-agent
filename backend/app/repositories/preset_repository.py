from typing import Any

from sqlalchemy.orm import Session

from app.models.preset import Preset


class PresetRepository:
    @staticmethod
    def create(session_db: Session, preset: Preset) -> Preset:
        session_db.add(preset)
        return preset

    @staticmethod
    def get_by_id(
        session_db: Session,
        preset_id: int,
        user_id: str,
        *,
        include_deleted: bool = False,
    ) -> Preset | None:
        query = session_db.query(Preset).filter(
            Preset.id == preset_id,
            Preset.user_id == user_id,
        )
        if not include_deleted:
            query = query.filter(Preset.is_deleted.is_(False))
        return query.first()

    @staticmethod
    def list_by_user(
        session_db: Session,
        user_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Preset]:
        query = session_db.query(Preset).filter(Preset.user_id == user_id)
        if not include_deleted:
            query = query.filter(Preset.is_deleted.is_(False))
        return query.order_by(Preset.created_at.desc()).all()

    @staticmethod
    def update(
        session_db: Session,
        preset: Preset,
        data: dict[str, Any],
    ) -> Preset:
        for key, value in data.items():
            setattr(preset, key, value)
        session_db.add(preset)
        return preset

    @staticmethod
    def soft_delete(session_db: Session, preset: Preset) -> None:
        preset.is_deleted = True
        session_db.add(preset)

    @staticmethod
    def exists_by_user_name(
        session_db: Session,
        user_id: str,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        query = session_db.query(Preset).filter(
            Preset.user_id == user_id,
            Preset.name == name,
            Preset.is_deleted.is_(False),
        )
        if exclude_id is not None:
            query = query.filter(Preset.id != exclude_id)
        return query.first() is not None
