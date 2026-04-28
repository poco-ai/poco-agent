from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.mcp_server import McpServer
from app.repositories.mcp_server_repository import McpServerRepository
from app.schemas.mcp_server import (
    McpServerAdminResponse,
    McpServerCreateRequest,
    McpServerResponse,
    McpServerUpdateRequest,
)
from app.services.admin_masking import mask_sensitive_structure
from app.utils.mcp_server_config import (
    extract_single_mcp_server_key,
    normalize_mcp_server_config,
)


def _normalize_description(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class McpServerService:
    def list_servers(self, db: Session, user_id: str) -> list[McpServerResponse]:
        servers = McpServerRepository.list_visible(db, user_id=user_id)
        return [self._to_response(s) for s in servers]

    def list_servers_for_admin(
        self, db: Session, user_id: str
    ) -> list[McpServerAdminResponse]:
        servers = McpServerRepository.list_visible(db, user_id=user_id)
        return [self._to_admin_response(server) for server in servers]

    def get_server(
        self, db: Session, user_id: str, server_id: int
    ) -> McpServerResponse:
        server = McpServerRepository.get_by_id(db, server_id)
        if not server or (server.scope == "user" and server.owner_user_id != user_id):
            raise AppException(
                error_code=ErrorCode.MCP_SERVER_NOT_FOUND,
                message=f"MCP server not found: {server_id}",
            )
        return self._to_response(server)

    def create_server(
        self, db: Session, user_id: str, request: McpServerCreateRequest
    ) -> McpServerResponse:
        scope = request.scope or "user"

        if McpServerRepository.get_by_name(db, request.name, user_id):
            raise AppException(
                error_code=ErrorCode.MCP_SERVER_ALREADY_EXISTS,
                message=f"MCP server already exists: {request.name}",
            )

        normalized_config = normalize_mcp_server_config(
            request.server_config,
            default_server_key=request.name,
        )
        server = McpServer(
            name=request.name,
            description=_normalize_description(request.description),
            scope=scope,
            owner_user_id=user_id,
            server_config=normalized_config,
            default_enabled=bool(request.default_enabled),
            force_enabled=bool(request.force_enabled),
        )

        McpServerRepository.create(db, server)
        db.commit()
        db.refresh(server)
        return self._to_response(server)

    def update_server(
        self,
        db: Session,
        user_id: str,
        server_id: int,
        request: McpServerUpdateRequest,
    ) -> McpServerResponse:
        server = McpServerRepository.get_by_id(db, server_id)
        if not server:
            raise AppException(
                error_code=ErrorCode.MCP_SERVER_NOT_FOUND,
                message=f"MCP server not found: {server_id}",
            )
        if server.scope == "system" and user_id != "__system__":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot modify system MCP servers",
            )
        if server.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="MCP server does not belong to the user",
            )

        if request.name is not None and request.name != server.name:
            if McpServerRepository.get_by_name(db, request.name, user_id):
                raise AppException(
                    error_code=ErrorCode.MCP_SERVER_ALREADY_EXISTS,
                    message=f"MCP server already exists: {request.name}",
                )
            server.name = request.name

        if request.scope is not None:
            server.scope = request.scope
        if request.description is not None:
            server.description = _normalize_description(request.description)
        if request.server_config is not None:
            default_key = (
                extract_single_mcp_server_key(server.server_config) or server.name
            )
            server.server_config = normalize_mcp_server_config(
                request.server_config,
                default_server_key=default_key,
            )
        if request.default_enabled is not None:
            server.default_enabled = bool(request.default_enabled)
        if request.force_enabled is not None:
            server.force_enabled = bool(request.force_enabled)

        db.commit()
        db.refresh(server)
        return self._to_response(server)

    def delete_server(self, db: Session, user_id: str, server_id: int) -> None:
        server = McpServerRepository.get_by_id(db, server_id)
        if not server:
            raise AppException(
                error_code=ErrorCode.MCP_SERVER_NOT_FOUND,
                message=f"MCP server not found: {server_id}",
            )
        if server.scope == "system" and user_id != "__system__":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot delete system MCP servers",
            )
        if server.owner_user_id != user_id:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="MCP server does not belong to the user",
            )
        McpServerRepository.delete(db, server)
        db.commit()

    @staticmethod
    def _to_response(server: McpServer) -> McpServerResponse:
        response_server_config = server.server_config
        has_sensitive_data = False
        if server.scope == "system":
            response_server_config, has_sensitive_data = mask_sensitive_structure(
                server.server_config
            )
        return McpServerResponse(
            id=server.id,
            name=server.name,
            description=server.description,
            scope=server.scope,
            owner_user_id=server.owner_user_id,
            server_config=response_server_config,
            has_sensitive_data=has_sensitive_data,
            default_enabled=bool(server.default_enabled),
            force_enabled=bool(server.force_enabled),
            created_at=server.created_at,
            updated_at=server.updated_at,
        )

    @staticmethod
    def _to_admin_response(server: McpServer) -> McpServerAdminResponse:
        masked_server_config, has_sensitive_data = mask_sensitive_structure(
            server.server_config
        )
        return McpServerAdminResponse(
            id=server.id,
            name=server.name,
            description=server.description,
            server_config=server.server_config,
            scope=server.scope,
            owner_user_id=server.owner_user_id,
            default_enabled=bool(server.default_enabled),
            force_enabled=bool(server.force_enabled),
            masked_server_config=masked_server_config,
            has_sensitive_data=has_sensitive_data,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )
