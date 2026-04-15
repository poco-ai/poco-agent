import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.audit import auditable
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.models.workspace_invite import WorkspaceInvite
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_invite_repository import WorkspaceInviteRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace_invite import (
    WorkspaceInviteAcceptRequest,
    WorkspaceInviteCreateRequest,
    WorkspaceInviteRevokeRequest,
    WorkspaceInviteResponse,
)
from app.schemas.workspace_member import WorkspaceMemberResponse
from app.services.workspace_member_service import (
    require_workspace_admin,
)


class WorkspaceInviteService:
    @staticmethod
    def _build_invite_response(invite: WorkspaceInvite) -> WorkspaceInviteResponse:
        return WorkspaceInviteResponse.model_validate(invite)

    @auditable(
        action="workspace.invite_created",
        target_type="invite",
        target_id=lambda _args, result: result.invite_id,
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda args, _result: {
            "role": args["request"].role,
            "max_uses": args["request"].max_uses,
        },
    )
    def create_invite(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
        request: WorkspaceInviteCreateRequest,
    ) -> WorkspaceInviteResponse:
        workspace = WorkspaceRepository.get_by_id(db, workspace_id)
        if workspace is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace not found: {workspace_id}",
            )
        require_workspace_admin(db, workspace_id, current_user.id)

        invite = WorkspaceInvite(
            workspace_id=workspace.id,
            token=secrets.token_urlsafe(24),
            role=request.role,
            expires_at=datetime.now(UTC) + timedelta(days=request.expires_in_days),
            created_by=current_user.id,
            max_uses=request.max_uses,
            used_count=0,
        )
        invite = WorkspaceInviteRepository.create(db, invite)
        db.commit()
        db.refresh(invite)
        return self._build_invite_response(invite)

    def list_invites(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceInviteResponse]:
        workspace = WorkspaceRepository.get_by_id(db, workspace_id)
        if workspace is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace not found: {workspace_id}",
            )
        require_workspace_admin(db, workspace_id, current_user.id)

        invites = WorkspaceInviteRepository.list_by_workspace(db, workspace_id)
        return [self._build_invite_response(item) for item in invites]

    @auditable(
        action="workspace.invite_revoked",
        target_type="invite",
        target_id=lambda args, _result: args["invite_id"],
        workspace_id=lambda args, _result: args["workspace_id"],
    )
    def revoke_invite(
        self,
        db: Session,
        current_user: User,
        workspace_id: uuid.UUID,
        invite_id: uuid.UUID,
        request: WorkspaceInviteRevokeRequest,
    ) -> WorkspaceInviteResponse:
        _ = request
        require_workspace_admin(db, workspace_id, current_user.id)
        invite = WorkspaceInviteRepository.get_by_id(db, invite_id)
        if invite is None or invite.workspace_id != workspace_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace invite not found: {invite_id}",
            )
        invite.revoked_at = datetime.now(UTC)
        db.commit()
        return self._build_invite_response(invite)

    @auditable(
        action="workspace.invite_accepted",
        target_type="invite",
        target_id=lambda args, _result: args["request"].token,
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda _args, result: {"user_id": result.user_id},
    )
    @auditable(
        action="workspace.member_joined",
        target_type="member",
        target_id=lambda _args, result: result.membership_id,
        workspace_id=lambda _args, result: result.workspace_id,
        metadata_fn=lambda _args, result: {
            "user_id": result.user_id,
            "role": result.role,
        },
    )
    def accept_invite(
        self,
        db: Session,
        current_user: User,
        request: WorkspaceInviteAcceptRequest,
    ) -> WorkspaceMemberResponse:
        token = request.token.strip()
        invite = WorkspaceInviteRepository.get_by_token(db, token)
        if invite is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Workspace invite not found",
            )
        workspace = WorkspaceRepository.get_by_id(db, invite.workspace_id)
        if workspace is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Workspace not found: {invite.workspace_id}",
            )
        if invite.revoked_at is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace invite has been revoked",
            )
        if invite.expires_at < datetime.now(UTC):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace invite has expired",
            )
        if invite.used_count >= invite.max_uses:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace invite has already been used",
            )

        existing_membership = WorkspaceMemberRepository.get_by_workspace_and_user(
            db,
            workspace.id,
            current_user.id,
        )
        if existing_membership is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="User is already a workspace member",
            )

        membership = WorkspaceMemberRepository.create(
            db,
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=current_user.id,
                role=invite.role,
                invited_by=invite.created_by,
                status="active",
            ),
        )
        invite.used_count += 1
        db.commit()
        if isinstance(membership, WorkspaceMember):
            db.refresh(membership)
        return WorkspaceMemberResponse.model_validate(membership)
