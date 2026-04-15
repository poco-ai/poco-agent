import uuid

from sqlalchemy.orm import Session

from app.core.audit import auditable
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.workspace_member import (
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdateRequest,
)


def _require_active_membership(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: str,
):
    membership = WorkspaceMemberRepository.get_by_workspace_and_user(
        db,
        workspace_id,
        user_id,
    )
    if membership is None or membership.status != "active":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="You are not a member of this workspace",
        )
    return membership


def require_workspace_member(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: str,
):
    return _require_active_membership(db, workspace_id, user_id)


def require_workspace_admin(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: str,
):
    membership = _require_active_membership(db, workspace_id, user_id)
    if membership.role not in {"owner", "admin"}:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="You do not have admin access to this workspace",
        )
    return membership


def require_workspace_owner(
    db: Session,
    workspace_id: uuid.UUID,
    user_id: str,
):
    membership = _require_active_membership(db, workspace_id, user_id)
    if membership.role != "owner":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Only workspace owners can perform this action",
        )
    return membership


class WorkspaceMemberService:
    def list_members(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMemberResponse]:
        require_workspace_member(db, workspace_id, current_user.id)

        members = WorkspaceMemberRepository.list_by_workspace(db, workspace_id)
        return [WorkspaceMemberResponse.model_validate(item) for item in members]

    @auditable(
        action="workspace.member_role_changed",
        target_type="member",
        target_id=lambda args, _result: args["membership_id"],
        workspace_id=lambda args, _result: args["workspace_id"],
        metadata_fn=lambda args, _result: {"role": args["request"].role},
    )
    def update_member_role(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
        membership_id: int,
        request: WorkspaceMemberRoleUpdateRequest,
    ) -> WorkspaceMemberResponse:
        require_workspace_owner(db, workspace_id, current_user.id)
        membership = WorkspaceMemberRepository.get_by_id(db, membership_id)
        if membership is None or membership.workspace_id != workspace_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace membership not found: {membership_id}",
            )
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Owner role cannot be changed directly",
            )
        membership.role = request.role
        db.commit()
        return WorkspaceMemberResponse.model_validate(membership)

    @auditable(
        action="workspace.member_removed",
        target_type="member",
        target_id=lambda args, _result: args["membership_id"],
        workspace_id=lambda args, _result: args["workspace_id"],
    )
    def remove_member(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
        membership_id: int,
    ) -> None:
        require_workspace_owner(db, workspace_id, current_user.id)
        membership = WorkspaceMemberRepository.get_by_id(db, membership_id)
        if membership is None or membership.workspace_id != workspace_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace membership not found: {membership_id}",
            )
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace owner cannot be removed",
            )
        db.delete(membership)
        db.commit()

    @auditable(
        action="workspace.member_left",
        target_type="member",
        target_id=lambda args, _result: args["current_user"].id,
        workspace_id=lambda args, _result: args["workspace_id"],
    )
    def leave_workspace(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
    ) -> None:
        membership = require_workspace_member(db, workspace_id, current_user.id)
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace owner cannot leave without transferring ownership",
            )
        db.delete(membership)
        db.commit()
