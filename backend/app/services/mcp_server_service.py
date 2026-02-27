from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.mcp_server import McpServer
from app.repositories.mcp_server_repository import McpServerRepository
from app.schemas.mcp_server import (
    McpServerCreateRequest,
    McpServerResponse,
    McpServerUpdateRequest,
)
from app.utils.mcp_server_config import (
    extract_single_mcp_server_key,
    normalize_mcp_server_config,
)


class McpServerService:
    def list_servers(self, db: Session, user_id: str) -> list[McpServerResponse]:
        servers = McpServerRepository.list_visible(db, user_id=user_id)
        return [self._to_response(s) for s in servers]

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
            scope=scope,
            owner_user_id=user_id,
            server_config=normalized_config,
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
        if server.scope == "system":
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
        if request.server_config is not None:
            default_key = (
                extract_single_mcp_server_key(server.server_config) or server.name
            )
            server.server_config = normalize_mcp_server_config(
                request.server_config,
                default_server_key=default_key,
            )

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
        if server.scope == "system":
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
        return McpServerResponse(
            id=server.id,
            name=server.name,
            scope=server.scope,
            owner_user_id=server.owner_user_id,
            server_config=server.server_config,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )
