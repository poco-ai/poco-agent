from sqlalchemy.orm import Session

from app.repositories.mcp_server_repository import McpServerRepository
from app.repositories.user_mcp_install_repository import UserMcpInstallRepository


class McpConfigService:
    """Service for building effective MCP config used by the executor."""

    def resolve_user_mcp_config(
        self,
        db: Session,
        user_id: str,
        server_ids: list[int],
    ) -> dict:
        """Resolve MCP config for a user given selected server ids.

        Args:
            db: Database session.
            user_id: User ID.
            server_ids: Selected MCP server ids for this run/session.

        Returns:
            MCP config dict compatible with Claude Agent SDK mcp_servers option:
            {server_name: server_config, ...}
        """
        installs = UserMcpInstallRepository.list_by_user(db, user_id)
        installs_by_server_id = {install.server_id: install for install in installs}

        # Preserve caller ordering but avoid duplicates.
        ordered_ids: list[int] = []
        seen: set[int] = set()
        for sid in server_ids:
            if sid in seen:
                continue
            seen.add(sid)
            ordered_ids.append(sid)

        resolved: dict = {}
        for server_id in ordered_ids:
            server = McpServerRepository.get_by_id(db, server_id)
            if not server or not isinstance(server.server_config, dict):
                continue
            install = installs_by_server_id.get(server_id)
            is_enabled = bool(server.force_enabled) or bool(
                install.enabled if install is not None else server.default_enabled
            )
            if not is_enabled:
                continue
            server_mcp = server.server_config.get("mcpServers")
            if not isinstance(server_mcp, dict):
                continue
            resolved = {**resolved, **server_mcp}

        if server_ids:
            requested_ids = set(ordered_ids)
        else:
            requested_ids = set()

        for server in McpServerRepository.list_visible(db, user_id=user_id):
            if server.scope != "system" or server.id in requested_ids:
                continue
            install = installs_by_server_id.get(server.id)
            is_enabled = bool(server.force_enabled) or bool(
                install.enabled if install is not None else server.default_enabled
            )
            if not is_enabled:
                continue
            server_mcp = server.server_config.get("mcpServers")
            if not isinstance(server_mcp, dict):
                continue
            resolved = {**resolved, **server_mcp}

        return resolved
