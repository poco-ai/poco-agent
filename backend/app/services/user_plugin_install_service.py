from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user_plugin_install import UserPluginInstall
from app.repositories.plugin_repository import PluginRepository
from app.repositories.user_plugin_install_repository import UserPluginInstallRepository
from app.schemas.user_plugin_install import (
    UserPluginInstallBulkUpdateRequest,
    UserPluginInstallBulkUpdateResponse,
    UserPluginInstallCreateRequest,
    UserPluginInstallResponse,
    UserPluginInstallUpdateRequest,
)


class UserPluginInstallService:
    def list_installs(
        self, db: Session, user_id: str
    ) -> list[UserPluginInstallResponse]:
        installs = UserPluginInstallRepository.list_by_user(db, user_id)
        return [self._to_response(i) for i in installs]

    def create_install(
        self, db: Session, user_id: str, request: UserPluginInstallCreateRequest
    ) -> UserPluginInstallResponse:
        plugin = PluginRepository.get_by_id(db, request.plugin_id)
        if not plugin or (plugin.scope != "system" and plugin.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.PLUGIN_NOT_FOUND,
                message=f"Plugin not found: {request.plugin_id}",
            )

        existing = UserPluginInstallRepository.get_by_user_and_plugin(
            db, user_id, request.plugin_id
        )
        if existing:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Plugin install already exists for plugin",
            )

        install = UserPluginInstall(
            user_id=user_id,
            plugin_id=request.plugin_id,
            enabled=(
                bool(plugin.force_enabled) or request.enabled
                if request.enabled is not None
                else bool(plugin.default_enabled or plugin.force_enabled)
            ),
        )
        UserPluginInstallRepository.create(db, install)
        db.commit()
        db.refresh(install)
        return self._to_response(install)

    def update_install(
        self,
        db: Session,
        user_id: str,
        install_id: int,
        request: UserPluginInstallUpdateRequest,
    ) -> UserPluginInstallResponse:
        install = UserPluginInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Plugin install not found: {install_id}",
            )

        if request.enabled is not None:
            plugin = PluginRepository.get_by_id(db, install.plugin_id)
            if (
                plugin
                and plugin.scope == "system"
                and plugin.force_enabled
                and not request.enabled
            ):
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system plugins",
                )
            install.enabled = request.enabled

        db.commit()
        db.refresh(install)
        return self._to_response(install)

    def bulk_update_installs(
        self,
        db: Session,
        user_id: str,
        request: UserPluginInstallBulkUpdateRequest,
    ) -> UserPluginInstallBulkUpdateResponse:
        if request.enabled is False:
            installs = UserPluginInstallRepository.list_by_user(db, user_id)
            target_ids = set(
                request.install_ids or [install.id for install in installs]
            )
            forced_install_ids = {
                install.id
                for install in installs
                if install.id in target_ids
                and (
                    (plugin := PluginRepository.get_by_id(db, install.plugin_id))
                    is not None
                    and plugin.scope == "system"
                    and plugin.force_enabled
                )
            }
            if forced_install_ids:
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot disable forced system plugins",
                )
        updated_count = UserPluginInstallRepository.bulk_set_enabled(
            db,
            user_id=user_id,
            enabled=request.enabled,
            install_ids=request.install_ids,
        )
        db.commit()
        return UserPluginInstallBulkUpdateResponse(updated_count=updated_count)

    def delete_install(self, db: Session, user_id: str, install_id: int) -> None:
        install = UserPluginInstallRepository.get_by_id(db, install_id)
        if not install or install.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Plugin install not found: {install_id}",
            )
        UserPluginInstallRepository.delete(db, install)
        db.commit()

    @staticmethod
    def _to_response(install: UserPluginInstall) -> UserPluginInstallResponse:
        return UserPluginInstallResponse(
            id=install.id,
            user_id=install.user_id,
            plugin_id=install.plugin_id,
            enabled=install.enabled,
            created_at=install.created_at,
            updated_at=install.updated_at,
        )
