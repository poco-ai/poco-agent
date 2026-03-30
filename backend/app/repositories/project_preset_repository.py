import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.project_preset import ProjectPreset


class ProjectPresetRepository:
    @staticmethod
    def add_to_project(
        session_db: Session,
        project_preset: ProjectPreset,
    ) -> ProjectPreset:
        session_db.add(project_preset)
        return project_preset

    @staticmethod
    def list_by_project(
        session_db: Session,
        project_id: uuid.UUID,
    ) -> list[ProjectPreset]:
        return (
            session_db.query(ProjectPreset)
            .filter(ProjectPreset.project_id == project_id)
            .order_by(ProjectPreset.sort_order.asc(), ProjectPreset.created_at.asc())
            .all()
        )

    @staticmethod
    def get_by_project_and_preset(
        session_db: Session,
        project_id: uuid.UUID,
        preset_id: int,
    ) -> ProjectPreset | None:
        return (
            session_db.query(ProjectPreset)
            .filter(
                ProjectPreset.project_id == project_id,
                ProjectPreset.preset_id == preset_id,
            )
            .first()
        )

    @staticmethod
    def get_default_preset(
        session_db: Session,
        project_id: uuid.UUID,
    ) -> ProjectPreset | None:
        return (
            session_db.query(ProjectPreset)
            .filter(
                ProjectPreset.project_id == project_id,
                ProjectPreset.is_default.is_(True),
            )
            .first()
        )

    @staticmethod
    def set_default_preset(
        session_db: Session,
        project_id: uuid.UUID,
        preset_id: int,
    ) -> ProjectPreset | None:
        session_db.query(ProjectPreset).filter(
            ProjectPreset.project_id == project_id,
            ProjectPreset.is_default.is_(True),
        ).update(
            {
                ProjectPreset.is_default: False,
                ProjectPreset.updated_at: func.now(),
            },
            synchronize_session=False,
        )

        project_preset = ProjectPresetRepository.get_by_project_and_preset(
            session_db,
            project_id,
            preset_id,
        )
        if project_preset is None:
            return None

        project_preset.is_default = True
        session_db.add(project_preset)
        return project_preset

    @staticmethod
    def remove_from_project(
        session_db: Session,
        project_preset: ProjectPreset,
    ) -> None:
        session_db.delete(project_preset)

    @staticmethod
    def update_sort_order(
        session_db: Session,
        project_preset: ProjectPreset,
        sort_order: int,
    ) -> ProjectPreset:
        project_preset.sort_order = sort_order
        session_db.add(project_preset)
        return project_preset

    @staticmethod
    def is_preset_in_project(
        session_db: Session,
        project_id: uuid.UUID,
        preset_id: int,
    ) -> bool:
        return (
            session_db.query(ProjectPreset)
            .filter(
                ProjectPreset.project_id == project_id,
                ProjectPreset.preset_id == preset_id,
            )
            .first()
            is not None
        )
