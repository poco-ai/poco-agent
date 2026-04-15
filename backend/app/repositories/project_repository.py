import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.workspace_member import WorkspaceMember


class ProjectRepository:
    @staticmethod
    def create(session_db: Session, project: Project) -> Project:
        session_db.add(project)
        return project

    @staticmethod
    def get_by_id(
        session_db: Session,
        project_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> Project | None:
        query = (
            session_db.query(Project)
            .options(
                selectinload(Project.project_local_mounts),
                selectinload(Project.default_preset),
            )
            .filter(Project.id == project_id)
        )
        if not include_deleted:
            query = query.filter(Project.is_deleted.is_(False))
        return query.first()

    @staticmethod
    def get_visible_by_id(
        session_db: Session,
        project_id: uuid.UUID,
        user_id: str,
    ) -> Project | None:
        return (
            session_db.query(Project)
            .options(
                selectinload(Project.project_local_mounts),
                selectinload(Project.default_preset),
            )
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Project.workspace_id)
                & (WorkspaceMember.user_id == user_id)
                & (WorkspaceMember.status == "active"),
            )
            .filter(
                Project.id == project_id,
                Project.is_deleted.is_(False),
                (
                    (Project.user_id == user_id)
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
    ) -> list[Project]:
        query = (
            session_db.query(Project)
            .options(
                selectinload(Project.project_local_mounts),
                selectinload(Project.default_preset),
            )
            .filter(Project.user_id == user_id)
        )
        if not include_deleted:
            query = query.filter(Project.is_deleted.is_(False))
        return query.order_by(Project.created_at.desc()).all()

    @staticmethod
    def list_visible_by_user(
        session_db: Session,
        user_id: str,
    ) -> list[Project]:
        return (
            session_db.query(Project)
            .options(
                selectinload(Project.project_local_mounts),
                selectinload(Project.default_preset),
            )
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Project.workspace_id)
                & (WorkspaceMember.user_id == user_id)
                & (WorkspaceMember.status == "active"),
            )
            .filter(
                Project.is_deleted.is_(False),
                (
                    (Project.user_id == user_id)
                    | (WorkspaceMember.id.is_not(None))
                ),
            )
            .order_by(Project.created_at.desc())
            .all()
        )
