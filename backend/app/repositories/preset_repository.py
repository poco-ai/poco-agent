from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.models.preset import Preset
from app.models.project import Project
from app.models.workspace_member import WorkspaceMember


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
    def get_visible_by_id(
        session_db: Session,
        preset_id: int,
        user_id: str,
    ) -> Preset | None:
        return (
            session_db.query(Preset)
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Preset.workspace_id)
                & (WorkspaceMember.user_id == user_id)
                & (WorkspaceMember.status == "active"),
            )
            .filter(
                Preset.id == preset_id,
                Preset.is_deleted.is_(False),
                (
                    (Preset.scope == "system")
                    | (Preset.user_id == user_id)
                    | (WorkspaceMember.id.is_not(None))
                ),
            )
            .first()
        )

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
    def list_visible_by_user(
        session_db: Session,
        user_id: str,
    ) -> list[Preset]:
        return (
            session_db.query(Preset)
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Preset.workspace_id)
                & (WorkspaceMember.user_id == user_id)
                & (WorkspaceMember.status == "active"),
            )
            .filter(
                Preset.is_deleted.is_(False),
                (
                    (Preset.scope == "system")
                    | (Preset.user_id == user_id)
                    | (WorkspaceMember.id.is_not(None))
                ),
            )
            .order_by(Preset.created_at.desc())
            .all()
        )

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

    @staticmethod
    def exists_by_scope_name(
        session_db: Session,
        *,
        scope: str,
        name: str,
        user_id: str | None = None,
        workspace_id: uuid.UUID | None = None,
        exclude_id: int | None = None,
    ) -> bool:
        query = session_db.query(Preset).filter(
            Preset.scope == scope,
            Preset.name == name,
            Preset.is_deleted.is_(False),
        )
        if scope == "workspace":
            query = query.filter(Preset.workspace_id == workspace_id)
        else:
            query = query.filter(Preset.user_id == user_id)
        if exclude_id is not None:
            query = query.filter(Preset.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def count_projects_using_as_default(
        session_db: Session,
        preset_id: int,
    ) -> int:
        return (
            session_db.query(Project)
            .filter(
                Project.default_preset_id == preset_id,
                Project.is_deleted.is_(False),
            )
            .count()
        )
