from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user_mcp_install import UserMcpInstall
from app.repositories.mcp_server_repository import McpServerRepository
from app.repositories.user_mcp_install_repository import UserMcpInstallRepository
from app.schemas.user_mcp_install import (
    UserMcpInstallBulkUpdateRequest,
    UserMcpInstallBulkUpdateResponse,
    UserMcpInstallCreateRequest,
    UserMcpInstallResponse,
    UserMcpInstallUpdateRequest,
)


class UserMcpInstallService:
    def list_installs(self, db: Session, user_id: str) -> list[UserMcpInstallResponse]:
        installs = UserMcpInstallRepository.list_by_user(db, user_id)
        return [self._to_response(i) for i in installs]

    def create_install(
        self, db: Session, user_id: str, request: UserMcpInstallCreateRequest
    ) -> UserMcpInstallResponse:
        server = McpServerRepository.get_by_id(db, request.server_id)
        if not server or (server.scope != "system" and server.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.MCP_SERVER_NOT_FOUND,
                message=f"MCP server not found: {request.server_id}",
            )

        existing = UserMcpInstallRepository.get_by_user_and_server(
            db, user_id, request.server_id
        )
        if existing:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="MCP install already exists for server",
            )

        install = UserMcpInstall(
            user_id=user_id,
            server_id=request.server_id,
            enabled=(
                bool(server.force_enabled) or request.enabled
                if request.enabled is not None
                else bool(server.default_enabled or server.force_enabled)
            ),
        )

        UserMcpInstallRepository.create(db, install)
        db.commit()
        db.refresh(install)
        return self._to_response(install)

    def update_install(
        self,
        db: Session,
        user_id: str,
        install_id: int,
        request: UserMcpInstallUpdateRequest,
    ) -> UserMcpInstallResponse:
        install = UserMcpInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"MCP install not found: {install_id}",
            )

        if request.enabled is not None:
            server = McpServerRepository.get_by_id(db, install.server_id)
            if (
                server
                and server.scope == "system"
                and server.force_enabled
                and not request.enabled
            ):
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system MCP servers",
                )
            install.enabled = request.enabled

        db.commit()
        db.refresh(install)
        return self._to_response(install)

    def bulk_update_installs(
        self,
        db: Session,
        user_id: str,
        request: UserMcpInstallBulkUpdateRequest,
    ) -> UserMcpInstallBulkUpdateResponse:
        if request.enabled is False:
            installs = UserMcpInstallRepository.list_by_user(db, user_id)
            target_ids = set(
                request.install_ids or [install.id for install in installs]
            )
            forced_install_ids = {
                install.id
                for install in installs
                if install.id in target_ids
                and (
                    (server := McpServerRepository.get_by_id(db, install.server_id))
                    is not None
                    and server.scope == "system"
                    and server.force_enabled
                )
            }
            if forced_install_ids:
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system MCP servers",
                )
        updated_count = UserMcpInstallRepository.bulk_set_enabled(
            db,
            user_id=user_id,
            enabled=request.enabled,
            install_ids=request.install_ids,
        )
        db.commit()
        return UserMcpInstallBulkUpdateResponse(updated_count=updated_count)

    def delete_install(self, db: Session, user_id: str, install_id: int) -> None:
        install = UserMcpInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"MCP install not found: {install_id}",
            )
        UserMcpInstallRepository.delete(db, install)
        db.commit()

    @staticmethod
    def _to_response(install: UserMcpInstall) -> UserMcpInstallResponse:
        return UserMcpInstallResponse(
            id=install.id,
            user_id=install.user_id,
            server_id=install.server_id,
            enabled=install.enabled,
            created_at=install.created_at,
            updated_at=install.updated_at,
        )
