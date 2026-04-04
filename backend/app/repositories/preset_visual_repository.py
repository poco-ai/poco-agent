from sqlalchemy.orm import Session

from app.models.preset_visual import PresetVisual


class PresetVisualRepository:
    @staticmethod
    def create(session_db: Session, preset_visual: PresetVisual) -> PresetVisual:
        session_db.add(preset_visual)
        return preset_visual

    @staticmethod
    def get_by_key(session_db: Session, key: str) -> PresetVisual | None:
        return (
            session_db.query(PresetVisual)
            .filter(PresetVisual.key == key)
            .first()
        )

    @staticmethod
    def list_active(session_db: Session) -> list[PresetVisual]:
        return (
            session_db.query(PresetVisual)
            .filter(PresetVisual.is_active.is_(True))
            .order_by(PresetVisual.key.asc())
            .all()
        )

    @staticmethod
    def list_managed(session_db: Session, *, managed_by: str) -> list[PresetVisual]:
        return (
            session_db.query(PresetVisual)
            .filter(PresetVisual.managed_by == managed_by)
            .order_by(PresetVisual.created_at.desc())
            .all()
        )
