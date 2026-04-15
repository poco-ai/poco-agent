from sqlalchemy.orm import Session

from app.models.workspace_issue import WorkspaceIssue
from app.models.workspace_issue_field_value import WorkspaceIssueFieldValue
from app.models.workspace_board_field import WorkspaceBoardField
from app.repositories.project_repository import ProjectRepository


class PromptBuilder:
    """Build execution prompts from workspace issues and related context."""

    def build_issue_prompt(
        self,
        db: Session,
        issue: WorkspaceIssue,
    ) -> str:
        sections: list[str] = [issue.title.strip()]

        description = (issue.description or "").strip()
        if description:
            sections.append(description)

        project = (
            ProjectRepository.get_by_id(db, issue.related_project_id)
            if issue.related_project_id is not None
            else None
        )
        if project is not None:
            project_lines = [f"Project: {project.name}"]
            if project.description:
                project_lines.append(f"Description: {project.description.strip()}")
            if project.repo_url:
                project_lines.append(f"Repository: {project.repo_url.strip()}")
            if project.git_branch:
                project_lines.append(f"Branch: {project.git_branch.strip()}")
            sections.append("\n".join(project_lines))

        field_rows = (
            db.query(WorkspaceBoardField.label, WorkspaceIssueFieldValue.value)
            .join(
                WorkspaceIssueFieldValue,
                WorkspaceIssueFieldValue.field_id == WorkspaceBoardField.id,
            )
            .filter(WorkspaceIssueFieldValue.issue_id == issue.id)
            .order_by(WorkspaceBoardField.sort_order.asc(), WorkspaceBoardField.label.asc())
            .all()
        )
        if field_rows:
            custom_lines = ["Custom fields:"]
            for label, value in field_rows:
                custom_lines.append(f"- {label}: {value}")
            sections.append("\n".join(custom_lines))

        return "\n\n".join(section for section in sections if section.strip())
