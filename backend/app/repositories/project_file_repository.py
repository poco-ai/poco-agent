import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.project_file import ProjectFile


class ProjectFileRepository:
    @staticmethod
    def create(session_db: Session, project_file: ProjectFile) -> ProjectFile:
        session_db.add(project_file)
        return project_file

    @staticmethod
    def list_by_project(
        session_db: Session,
        project_id: uuid.UUID,
    ) -> list[ProjectFile]:
        return (
            session_db.query(ProjectFile)
            .filter(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.sort_order.asc(), ProjectFile.created_at.asc())
            .all()
        )

    @staticmethod
    def get_by_id(session_db: Session, file_id: int) -> ProjectFile | None:
        return session_db.query(ProjectFile).filter(ProjectFile.id == file_id).first()

    @staticmethod
    def delete(session_db: Session, project_file: ProjectFile) -> None:
        session_db.delete(project_file)

    @staticmethod
    def get_max_sort_order(session_db: Session, project_id: uuid.UUID) -> int:
        value = (
            session_db.query(func.max(ProjectFile.sort_order))
            .filter(ProjectFile.project_id == project_id)
            .scalar()
        )
        return int(value or 0)
