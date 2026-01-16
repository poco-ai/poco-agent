from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.mcp_preset import McpPreset


class McpPresetRepository:
    @staticmethod
    def create(session_db: Session, preset: McpPreset) -> McpPreset:
        session_db.add(preset)
        return preset

    @staticmethod
    def get_by_id(session_db: Session, preset_id: int) -> McpPreset | None:
        return session_db.query(McpPreset).filter(McpPreset.id == preset_id).first()

    @staticmethod
    def get_by_name(session_db: Session, name: str) -> McpPreset | None:
        return session_db.query(McpPreset).filter(McpPreset.name == name).first()

    @staticmethod
    def list_all(
        session_db: Session, include_inactive: bool = False
    ) -> list[McpPreset]:
        query = session_db.query(McpPreset)
        if not include_inactive:
            query = query.filter(McpPreset.is_active.is_(True))
        return query.order_by(McpPreset.created_at.desc()).all()

    @staticmethod
    def list_visible(
        session_db: Session, user_id: str, include_inactive: bool = False
    ) -> list[McpPreset]:
        query = session_db.query(McpPreset).filter(
            or_(McpPreset.source == "system", McpPreset.owner_user_id == user_id)
        )
        if not include_inactive:
            query = query.filter(McpPreset.is_active.is_(True))
        return query.order_by(McpPreset.created_at.desc()).all()

    @staticmethod
    def delete(session_db: Session, preset: McpPreset) -> None:
        session_db.delete(preset)
