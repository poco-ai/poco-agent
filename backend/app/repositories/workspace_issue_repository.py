import uuid

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.models.workspace_issue import WorkspaceIssue


class WorkspaceIssueRepository:
    _STATUS_ORDER = case(
        (WorkspaceIssue.status == "todo", 0),
        (WorkspaceIssue.status == "in_progress", 1),
        (WorkspaceIssue.status == "done", 2),
        (WorkspaceIssue.status == "canceled", 3),
        else_=99,
    )

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
            .order_by(
                WorkspaceIssueRepository._STATUS_ORDER,
                WorkspaceIssue.position.asc(),
                WorkspaceIssue.updated_at.desc(),
                WorkspaceIssue.created_at.desc(),
            )
            .all()
        )

    @staticmethod
    def list_by_board_and_status(
        session_db: Session,
        board_id: uuid.UUID,
        status: str,
        *,
        exclude_issue_id: uuid.UUID | None = None,
    ) -> list[WorkspaceIssue]:
        query = session_db.query(WorkspaceIssue).filter(
            WorkspaceIssue.board_id == board_id,
            WorkspaceIssue.status == status,
        )
        if exclude_issue_id is not None:
            query = query.filter(WorkspaceIssue.id != exclude_issue_id)
        return (
            query.order_by(
                WorkspaceIssue.position.asc(),
                WorkspaceIssue.updated_at.desc(),
                WorkspaceIssue.created_at.desc(),
            ).all()
        )
