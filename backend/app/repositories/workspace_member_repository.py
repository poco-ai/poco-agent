import uuid

from sqlalchemy.orm import Session

from app.models.workspace_member import WorkspaceMember


class WorkspaceMemberRepository:
    @staticmethod
    def create(session_db: Session, membership: WorkspaceMember) -> WorkspaceMember:
        session_db.add(membership)
        return membership

    @staticmethod
    def get_by_workspace_and_user(
        session_db: Session,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> WorkspaceMember | None:
        return (
            session_db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def list_by_workspace(
        session_db: Session,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMember]:
        return (
            session_db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc(), WorkspaceMember.id.asc())
            .all()
        )
