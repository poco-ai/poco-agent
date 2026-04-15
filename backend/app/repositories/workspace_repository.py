import uuid

from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class WorkspaceRepository:
    @staticmethod
    def create(session_db: Session, workspace: Workspace) -> Workspace:
        session_db.add(workspace)
        return workspace

    @staticmethod
    def get_by_id(session_db: Session, workspace_id: uuid.UUID) -> Workspace | None:
        return session_db.query(Workspace).filter(Workspace.id == workspace_id).first()

    @staticmethod
    def get_by_slug(session_db: Session, slug: str) -> Workspace | None:
        return session_db.query(Workspace).filter(Workspace.slug == slug).first()

    @staticmethod
    def get_personal_by_owner(
        session_db: Session,
        owner_user_id: str,
    ) -> Workspace | None:
        return (
            session_db.query(Workspace)
            .filter(
                Workspace.owner_user_id == owner_user_id,
                Workspace.kind == "personal",
            )
            .first()
        )

    @staticmethod
    def list_by_user(session_db: Session, user_id: str) -> list[Workspace]:
        return (
            session_db.query(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
            )
            .order_by(Workspace.created_at.desc())
            .all()
        )
