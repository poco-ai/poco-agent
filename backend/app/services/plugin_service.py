import re

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.plugin import Plugin
from app.repositories.plugin_repository import PluginRepository
from app.schemas.plugin import (
    PluginAdminResponse,
    PluginCreateRequest,
    PluginResponse,
    PluginUpdateRequest,
)
from app.schemas.source import SourceInfo
from app.services.admin_masking import mask_sensitive_structure
from app.services.source_utils import infer_capability_source


_PLUGIN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_plugin_name(name: str) -> str:
    value = (name or "").strip()
    if not value or value in {".", ".."} or not _PLUGIN_NAME_PATTERN.fullmatch(value):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Invalid plugin name: {name}",
        )
    return value


class PluginService:
    def list_plugins(self, db: Session, user_id: str) -> list[PluginResponse]:
        plugins = PluginRepository.list_visible(db, user_id=user_id)
        return [self._to_response(p) for p in plugins]

    def list_plugins_for_admin(
        self, db: Session, user_id: str
    ) -> list[PluginAdminResponse]:
        plugins = PluginRepository.list_visible(db, user_id=user_id)
        return [self._to_admin_response(plugin) for plugin in plugins]

    def get_plugin(self, db: Session, user_id: str, plugin_id: int) -> PluginResponse:
        plugin = PluginRepository.get_by_id(db, plugin_id)
        if not plugin or (plugin.scope != "system" and plugin.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.PLUGIN_NOT_FOUND,
                message=f"Plugin not found: {plugin_id}",
            )
        return self._to_response(plugin)

    def create_plugin(
        self, db: Session, user_id: str, request: PluginCreateRequest
    ) -> PluginResponse:
        name = _validate_plugin_name(request.name)
        scope = (request.scope or "user").strip() or "user"

        if PluginRepository.get_by_name(db, name, user_id):
            raise AppException(
                error_code=ErrorCode.PLUGIN_ALREADY_EXISTS,
                message=f"Plugin already exists: {name}",
            )

        plugin = Plugin(
            name=name,
            scope=scope,
            owner_user_id=user_id,
            description=request.description,
            version=request.version,
            manifest=request.manifest,
            entry=request.entry or {},
            source={"kind": "manual"},
            default_enabled=bool(request.default_enabled),
            force_enabled=bool(request.force_enabled),
        )
        PluginRepository.create(db, plugin)
        db.commit()
        db.refresh(plugin)
        return self._to_response(plugin)

    def update_plugin(
        self,
        db: Session,
        user_id: str,
        plugin_id: int,
        request: PluginUpdateRequest,
    ) -> PluginResponse:
        plugin = PluginRepository.get_by_id(db, plugin_id)
        if not plugin:
            raise AppException(
                error_code=ErrorCode.PLUGIN_NOT_FOUND,
                message=f"Plugin not found: {plugin_id}",
            )
        if plugin.scope == "system" and user_id != "__system__":
            raise AppException(
                error_code=ErrorCode.PLUGIN_MODIFY_FORBIDDEN,
                message="Cannot modify system plugins",
            )
        if plugin.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Plugin does not belong to the user",
            )

        if (
            request.name is not None
            and request.name.strip()
            and request.name.strip() != plugin.name
        ):
            new_name = _validate_plugin_name(request.name)
            if PluginRepository.get_by_name(db, new_name, user_id):
                raise AppException(
                    error_code=ErrorCode.PLUGIN_ALREADY_EXISTS,
                    message=f"Plugin already exists: {new_name}",
                )
            plugin.name = new_name

        if request.scope is not None and request.scope.strip():
            plugin.scope = request.scope.strip()
        if request.description is not None:
            plugin.description = request.description
        if request.version is not None:
            plugin.version = request.version
        if request.manifest is not None:
            plugin.manifest = request.manifest
        if request.entry is not None:
            plugin.entry = request.entry
        if request.default_enabled is not None:
            plugin.default_enabled = bool(request.default_enabled)
        if request.force_enabled is not None:
            plugin.force_enabled = bool(request.force_enabled)

        db.commit()
        db.refresh(plugin)
        return self._to_response(plugin)

    def delete_plugin(self, db: Session, user_id: str, plugin_id: int) -> None:
        plugin = PluginRepository.get_by_id(db, plugin_id)
        if not plugin:
            raise AppException(
                error_code=ErrorCode.PLUGIN_NOT_FOUND,
                message=f"Plugin not found: {plugin_id}",
            )
        if plugin.scope == "system" and user_id != "__system__":
            raise AppException(
                error_code=ErrorCode.PLUGIN_MODIFY_FORBIDDEN,
                message="Cannot delete system plugins",
            )
        if plugin.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Plugin does not belong to the user",
            )

        PluginRepository.delete(db, plugin)
        db.commit()

    @staticmethod
    def _to_response(plugin: Plugin) -> PluginResponse:
        source_dict = infer_capability_source(
            scope=plugin.scope,
            source=getattr(plugin, "source", None),
            entry=plugin.entry,
        )
        return PluginResponse(
            id=plugin.id,
            name=plugin.name,
            entry=plugin.entry,
            source=SourceInfo.model_validate(source_dict),
            scope=plugin.scope,
            owner_user_id=plugin.owner_user_id,
            default_enabled=bool(plugin.default_enabled),
            force_enabled=bool(plugin.force_enabled),
            description=plugin.description,
            version=plugin.version,
            manifest=plugin.manifest,
            created_at=plugin.created_at,
            updated_at=plugin.updated_at,
        )

    @staticmethod
    def _to_admin_response(plugin: Plugin) -> PluginAdminResponse:
        source_dict = infer_capability_source(
            scope=plugin.scope,
            source=getattr(plugin, "source", None),
            entry=plugin.entry,
        )
        masked_entry, entry_has_sensitive_data = mask_sensitive_structure(plugin.entry)
        masked_manifest, manifest_has_sensitive_data = mask_sensitive_structure(
            plugin.manifest
        )
        return PluginAdminResponse(
            id=plugin.id,
            name=plugin.name,
            masked_entry=masked_entry,
            masked_manifest=masked_manifest,
            entry_has_sensitive_data=entry_has_sensitive_data,
            manifest_has_sensitive_data=manifest_has_sensitive_data,
            source=SourceInfo.model_validate(source_dict),
            scope=plugin.scope,
            owner_user_id=plugin.owner_user_id,
            default_enabled=bool(plugin.default_enabled),
            force_enabled=bool(plugin.force_enabled),
            description=plugin.description,
            version=plugin.version,
            created_at=plugin.created_at,
            updated_at=plugin.updated_at,
        )
