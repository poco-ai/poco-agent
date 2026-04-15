import uuid

from sqlalchemy.orm import Session

from app.models.workspace_invite import WorkspaceInvite


class WorkspaceInviteRepository:
    @staticmethod
    def create(session_db: Session, invite: WorkspaceInvite) -> WorkspaceInvite:
        session_db.add(invite)
        return invite

    @staticmethod
    def get_by_token(session_db: Session, token: str) -> WorkspaceInvite | None:
        return (
            session_db.query(WorkspaceInvite)
            .filter(WorkspaceInvite.token == token)
            .first()
        )

    @staticmethod
    def list_by_workspace(
        session_db: Session,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceInvite]:
        return (
            session_db.query(WorkspaceInvite)
            .filter(WorkspaceInvite.workspace_id == workspace_id)
            .order_by(WorkspaceInvite.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(
        session_db: Session,
        invite_id: uuid.UUID,
    ) -> WorkspaceInvite | None:
        return (
            session_db.query(WorkspaceInvite)
            .filter(WorkspaceInvite.id == invite_id)
            .first()
        )
