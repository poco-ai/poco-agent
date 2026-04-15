import uuid

from sqlalchemy.orm import Session

from app.models.workspace_board import WorkspaceBoard


class WorkspaceBoardRepository:
    @staticmethod
    def create(session_db: Session, board: WorkspaceBoard) -> WorkspaceBoard:
        session_db.add(board)
        return board

    @staticmethod
    def get_by_id(session_db: Session, board_id: uuid.UUID) -> WorkspaceBoard | None:
        return session_db.query(WorkspaceBoard).filter(WorkspaceBoard.id == board_id).first()

    @staticmethod
    def list_by_workspace(
        session_db: Session,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceBoard]:
        return (
            session_db.query(WorkspaceBoard)
            .filter(WorkspaceBoard.workspace_id == workspace_id)
            .order_by(WorkspaceBoard.created_at.desc())
            .all()
        )
