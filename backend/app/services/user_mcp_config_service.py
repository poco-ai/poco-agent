from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.user_mcp_config import UserMcpConfig
from app.repositories.mcp_preset_repository import McpPresetRepository
from app.repositories.user_mcp_config_repository import UserMcpConfigRepository
from app.schemas.user_mcp_config import (
    UserMcpConfigCreateRequest,
    UserMcpConfigResponse,
    UserMcpConfigUpdateRequest,
)


class UserMcpConfigService:
    def list_configs(self, db: Session, user_id: str) -> list[UserMcpConfigResponse]:
        configs = UserMcpConfigRepository.list_by_user(db, user_id)
        return [self._to_response(c) for c in configs]

    def create_config(
        self, db: Session, user_id: str, request: UserMcpConfigCreateRequest
    ) -> UserMcpConfigResponse:
        preset = McpPresetRepository.get_by_id(db, request.preset_id)
        if not preset or (
            preset.source != "system" and preset.owner_user_id != user_id
        ):
            raise AppException(
                error_code=ErrorCode.MCP_PRESET_NOT_FOUND,
                message=f"MCP preset not found: {request.preset_id}",
            )
        if not preset.is_active:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="MCP preset is inactive",
            )

        config = UserMcpConfig(
            user_id=user_id,
            preset_id=request.preset_id,
            enabled=request.enabled,
            overrides=request.overrides,
        )
        try:
            UserMcpConfigRepository.create(db, config)
            db.commit()
            db.refresh(config)
        except IntegrityError as exc:
            db.rollback()
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="MCP config already exists for preset",
            ) from exc

        return self._to_response(config)

    def update_config(
        self,
        db: Session,
        user_id: str,
        config_id: int,
        request: UserMcpConfigUpdateRequest,
    ) -> UserMcpConfigResponse:
        config = UserMcpConfigRepository.get_by_id(db, config_id)
        if not config or config.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"MCP config not found: {config_id}",
            )

        if request.enabled is not None:
            config.enabled = request.enabled
        if request.overrides is not None:
            config.overrides = request.overrides

        db.commit()
        db.refresh(config)
        return self._to_response(config)

    def delete_config(self, db: Session, user_id: str, config_id: int) -> None:
        config = UserMcpConfigRepository.get_by_id(db, config_id)
        if not config or config.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"MCP config not found: {config_id}",
            )
        UserMcpConfigRepository.delete(db, config)
        db.commit()

    @staticmethod
    def _to_response(config: UserMcpConfig) -> UserMcpConfigResponse:
        return UserMcpConfigResponse(
            id=config.id,
            user_id=config.user_id,
            preset_id=config.preset_id,
            enabled=config.enabled,
            overrides=config.overrides,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
