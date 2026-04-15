import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.workspace_member import WorkspaceMemberResponse


class WorkspaceMemberService:
    def list_members(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMemberResponse]:
        membership = WorkspaceMemberRepository.get_by_workspace_and_user(
            db,
            workspace_id,
            current_user.id,
        )
        if membership is None or membership.status != "active":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="You are not a member of this workspace",
            )

        members = WorkspaceMemberRepository.list_by_workspace(db, workspace_id)
        return [WorkspaceMemberResponse.model_validate(item) for item in members]
