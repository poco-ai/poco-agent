import re

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace_tenancy import WorkspaceCreateRequest, WorkspaceResponse


class WorkspaceService:
    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "workspace"

    @classmethod
    def _personal_workspace_name(cls, current_user: User) -> str:
        display_name = (current_user.display_name or "").strip()
        if display_name:
            return f"{display_name}'s Workspace"
        return "Personal Workspace"

    @classmethod
    def _personal_workspace_slug(cls, current_user: User) -> str:
        return cls._slugify(f"personal-{current_user.id}")

    @classmethod
    def _build_workspace_response(cls, workspace: Workspace) -> WorkspaceResponse:
        return WorkspaceResponse.model_validate(workspace)

    @classmethod
    def _unique_slug(cls, db: Session, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while WorkspaceRepository.get_by_slug(db, slug) is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    def ensure_personal_workspace(self, db: Session, current_user: User) -> Workspace:
        workspace = WorkspaceRepository.get_personal_by_owner(db, current_user.id)
        if workspace is not None:
            return workspace

        workspace = Workspace(
            name=self._personal_workspace_name(current_user),
            slug=self._unique_slug(db, self._personal_workspace_slug(current_user)),
            kind="personal",
            owner_user_id=current_user.id,
        )
        WorkspaceRepository.create(db, workspace)
        WorkspaceMemberRepository.create(
            db,
            WorkspaceMember(
                workspace=workspace,
                user_id=current_user.id,
                role="owner",
                invited_by=None,
                status="active",
            ),
        )
        db.commit()
        db.refresh(workspace)
        return workspace

    def list_workspaces(self, db: Session, current_user: User) -> list[WorkspaceResponse]:
        self.ensure_personal_workspace(db, current_user)
        workspaces = WorkspaceRepository.list_by_user(db, current_user.id)
        return [self._build_workspace_response(item) for item in workspaces]

    def create_workspace(
        self,
        db: Session,
        current_user: User,
        request: WorkspaceCreateRequest,
    ) -> WorkspaceResponse:
        name = request.name.strip()
        if not name:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Workspace name cannot be empty",
            )

        self.ensure_personal_workspace(db, current_user)
        workspace = Workspace(
            name=name,
            slug=self._unique_slug(db, self._slugify(name)),
            kind="shared",
            owner_user_id=current_user.id,
        )
        workspace = WorkspaceRepository.create(db, workspace)
        WorkspaceMemberRepository.create(
            db,
            WorkspaceMember(
                workspace=workspace,
                user_id=current_user.id,
                role="owner",
                invited_by=None,
                status="active",
            ),
        )
        db.commit()
        db.refresh(workspace)
        return self._build_workspace_response(workspace)
