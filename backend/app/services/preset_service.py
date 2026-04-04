from collections.abc import Callable, Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.mcp_server import McpServer
from app.models.plugin import Plugin
from app.models.preset import Preset
from app.models.preset_visual import PresetVisual
from app.models.skill import Skill
from app.repositories.mcp_server_repository import McpServerRepository
from app.repositories.plugin_repository import PluginRepository
from app.repositories.preset_repository import PresetRepository
from app.repositories.preset_visual_repository import PresetVisualRepository
from app.repositories.skill_repository import SkillRepository
from app.schemas.preset import (
    PresetCreateRequest,
    PresetResponse,
    PresetSubAgentConfig,
    PresetVisualSummary,
    PresetUpdateRequest,
)
from app.services.storage_service import S3StorageService

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ASSETS_ROOT = _REPO_ROOT / "assets"


class PresetService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service

    def list_presets(self, db: Session, user_id: str) -> list[PresetResponse]:
        presets = PresetRepository.list_by_user(db, user_id)
        return [self._to_response(db, item) for item in presets]

    def list_preset_visuals(self, db: Session) -> list[PresetVisualSummary]:
        visuals = PresetVisualRepository.list_active(db)
        return [
            PresetVisualSummary(
                key=visual.key,
                name=visual.name,
                version=visual.version,
                url=self._build_visual_url(visual),
            )
            for visual in visuals
        ]

    def get_preset(self, db: Session, user_id: str, preset_id: int) -> PresetResponse:
        preset = PresetRepository.get_by_id(db, preset_id, user_id)
        if not preset:
            raise AppException(
                error_code=ErrorCode.PRESET_NOT_FOUND,
                message=f"Preset not found: {preset_id}",
            )
        return self._to_response(db, preset)

    def create_preset(
        self, db: Session, user_id: str, request: PresetCreateRequest
    ) -> PresetResponse:
        name = request.name.strip()
        if PresetRepository.exists_by_user_name(db, user_id, name):
            raise AppException(
                error_code=ErrorCode.PRESET_ALREADY_EXISTS,
                message=f"Preset already exists: {name}",
            )

        self._validate_components(
            db,
            user_id=user_id,
            skill_ids=request.skill_ids,
            mcp_server_ids=request.mcp_server_ids,
            plugin_ids=request.plugin_ids,
        )
        visual = self._require_visual(db, request.visual_key)

        preset = Preset(
            user_id=user_id,
            name=name,
            description=self._normalize_optional_str(request.description),
            visual_key=visual.key,
            prompt_template=request.prompt_template,
            browser_enabled=request.browser_enabled,
            memory_enabled=request.memory_enabled,
            skill_ids=request.skill_ids,
            mcp_server_ids=request.mcp_server_ids,
            plugin_ids=request.plugin_ids,
            subagent_configs=[
                item.model_dump(mode="json") for item in request.subagent_configs
            ],
        )
        PresetRepository.create(db, preset)
        db.commit()
        db.refresh(preset)
        return self._to_response(db, preset)

    def update_preset(
        self,
        db: Session,
        user_id: str,
        preset_id: int,
        request: PresetUpdateRequest,
    ) -> PresetResponse:
        preset = PresetRepository.get_by_id(db, preset_id, user_id)
        if not preset:
            raise AppException(
                error_code=ErrorCode.PRESET_NOT_FOUND,
                message=f"Preset not found: {preset_id}",
            )

        update_data = request.model_dump(exclude_unset=True)
        if "name" in update_data:
            name = (request.name or "").strip()
            if not name:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Preset name cannot be empty",
                )
            if PresetRepository.exists_by_user_name(
                db, user_id, name, exclude_id=preset_id
            ):
                raise AppException(
                    error_code=ErrorCode.PRESET_ALREADY_EXISTS,
                    message=f"Preset already exists: {name}",
                )
            update_data["name"] = name

        if "description" in update_data:
            update_data["description"] = self._normalize_optional_str(
                request.description
            )
        if "visual_key" in update_data and request.visual_key is not None:
            update_data["visual_key"] = self._require_visual(
                db, request.visual_key
            ).key

        skill_ids = update_data.get("skill_ids", preset.skill_ids)
        mcp_server_ids = update_data.get("mcp_server_ids", preset.mcp_server_ids)
        plugin_ids = update_data.get("plugin_ids", preset.plugin_ids)
        self._validate_components(
            db,
            user_id=user_id,
            skill_ids=skill_ids,
            mcp_server_ids=mcp_server_ids,
            plugin_ids=plugin_ids,
        )

        if "subagent_configs" in update_data and request.subagent_configs is not None:
            update_data["subagent_configs"] = [
                item.model_dump(mode="json") for item in request.subagent_configs
            ]

        PresetRepository.update(db, preset, update_data)
        db.commit()
        db.refresh(preset)
        return self._to_response(db, preset)

    def delete_preset(self, db: Session, user_id: str, preset_id: int) -> None:
        preset = PresetRepository.get_by_id(db, preset_id, user_id)
        if not preset:
            raise AppException(
                error_code=ErrorCode.PRESET_NOT_FOUND,
                message=f"Preset not found: {preset_id}",
            )

        usage_count = PresetRepository.count_projects_using_as_default(db, preset_id)
        if usage_count > 0:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Preset is still used as a project default preset",
            )

        PresetRepository.soft_delete(db, preset)
        db.commit()

    def get_preset_visual_content(self, db: Session, visual_key: str) -> str:
        visual = PresetVisualRepository.get_by_key(db, visual_key)
        if visual is None or not visual.is_active:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Preset visual not found: {visual_key}",
            )

        storage_service = self._storage_service()
        if storage_service is not None:
            try:
                return storage_service.get_text(visual.storage_key)
            except AppException:
                pass

        local_path = self._resolve_local_visual_path(visual)
        if local_path is not None and local_path.exists():
            return local_path.read_text(encoding="utf-8")

        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Preset visual content not found: {visual_key}",
        )

    def _validate_components(
        self,
        db: Session,
        *,
        user_id: str,
        skill_ids: list[int],
        mcp_server_ids: list[int],
        plugin_ids: list[int],
    ) -> None:
        self._validate_visible_skills(db, user_id=user_id, skill_ids=skill_ids)
        self._validate_visible_mcp_servers(
            db, user_id=user_id, mcp_server_ids=mcp_server_ids
        )
        self._validate_visible_plugins(db, user_id=user_id, plugin_ids=plugin_ids)

    @staticmethod
    def _normalize_optional_str(value: str | None) -> str | None:
        clean = (value or "").strip()
        return clean or None

    def _to_response(self, db: Session, preset: Preset) -> PresetResponse:
        payload = PresetResponse.model_validate(preset)
        payload.subagent_configs = [
            PresetSubAgentConfig.model_validate(item)
            for item in preset.subagent_configs
        ]
        visual = PresetVisualRepository.get_by_key(db, preset.visual_key)
        if visual is not None and visual.is_active:
            payload.visual_name = visual.name
            payload.visual_version = visual.version
            payload.visual_url = self._build_visual_url(visual)
        return payload

    def _require_visual(self, db: Session, visual_key: str) -> PresetVisual:
        visual = PresetVisualRepository.get_by_key(db, visual_key)
        if visual is None or not visual.is_active:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid preset visual key: {visual_key}",
            )
        return visual

    def _build_visual_url(self, visual: PresetVisual) -> str:
        return f"/api/v1/presets/visuals/{visual.key}/content"

    def _storage_service(self) -> S3StorageService | None:
        if self.storage_service is not None:
            return self.storage_service
        try:
            self.storage_service = S3StorageService()
        except Exception:
            self.storage_service = None
        return self.storage_service

    @staticmethod
    def _resolve_local_visual_path(visual: PresetVisual) -> Path | None:
        source = (visual.source or "").strip().lstrip("/")
        if not source:
            return None
        path = (_ASSETS_ROOT / source).resolve()
        try:
            path.relative_to(_ASSETS_ROOT.resolve())
        except ValueError:
            return None
        return path

    @staticmethod
    def _validate_visible_skills(
        db: Session,
        *,
        user_id: str,
        skill_ids: list[int],
    ) -> None:
        skills = SkillRepository.list_by_ids(db, skill_ids)
        PresetService._validate_component_ids(
            requested_ids=skill_ids,
            items=skills,
            ownership_check=lambda item: (
                item.scope == "system" or item.owner_user_id == user_id
            ),
            component_name="skill",
        )

    @staticmethod
    def _validate_visible_mcp_servers(
        db: Session,
        *,
        user_id: str,
        mcp_server_ids: list[int],
    ) -> None:
        servers = [
            McpServerRepository.get_by_id(db, server_id) for server_id in mcp_server_ids
        ]
        PresetService._validate_component_ids(
            requested_ids=mcp_server_ids,
            items=[item for item in servers if item is not None],
            ownership_check=lambda item: (
                item.scope == "system" or item.owner_user_id == user_id
            ),
            component_name="MCP server",
        )

    @staticmethod
    def _validate_visible_plugins(
        db: Session,
        *,
        user_id: str,
        plugin_ids: list[int],
    ) -> None:
        plugins = [
            PluginRepository.get_by_id(db, plugin_id) for plugin_id in plugin_ids
        ]
        PresetService._validate_component_ids(
            requested_ids=plugin_ids,
            items=[item for item in plugins if item is not None],
            ownership_check=lambda item: (
                item.scope == "system" or item.owner_user_id == user_id
            ),
            component_name="plugin",
        )

    @staticmethod
    def _validate_component_ids(
        *,
        requested_ids: list[int],
        items: Sequence[Skill | McpServer | Plugin],
        ownership_check: Callable[[Skill | McpServer | Plugin], bool],
        component_name: str,
    ) -> None:
        if not requested_ids:
            return
        visible_ids = {item.id for item in items if ownership_check(item)}
        invalid_ids = [
            item_id for item_id in requested_ids if item_id not in visible_ids
        ]
        if invalid_ids:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid {component_name} ids: {invalid_ids}",
            )
