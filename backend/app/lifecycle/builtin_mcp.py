from sqlalchemy.orm import Session


class McpServerBootstrapService:
    """Placeholder bootstrap service for built-in MCP servers."""

    @classmethod
    def bootstrap_builtin_servers(cls, db: Session) -> None:
        """Bootstrap built-in MCP servers.

        Phase 1 only reserves the bootstrap slot for future MCP seeds.
        """
        del db
