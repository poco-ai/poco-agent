import uuid

from sqlalchemy.orm import Session

from app.models.workspace_issue import WorkspaceIssue


class WorkspaceIssueRepository:
    @staticmethod
    def create(session_db: Session, issue: WorkspaceIssue) -> WorkspaceIssue:
        session_db.add(issue)
        return issue

    @staticmethod
    def get_by_id(session_db: Session, issue_id: uuid.UUID) -> WorkspaceIssue | None:
        return session_db.query(WorkspaceIssue).filter(WorkspaceIssue.id == issue_id).first()

    @staticmethod
    def list_by_board(
        session_db: Session,
        board_id: uuid.UUID,
    ) -> list[WorkspaceIssue]:
        return (
            session_db.query(WorkspaceIssue)
            .filter(WorkspaceIssue.board_id == board_id)
            .order_by(WorkspaceIssue.created_at.desc())
            .all()
        )
