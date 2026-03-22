import logging

from app.core.database import SessionLocal
from app.lifecycle.builtin_mcp import McpServerBootstrapService
from app.lifecycle.builtin_skills import SkillBootstrapService

logger = logging.getLogger(__name__)


class LifecycleBootstrapService:
    """Bootstrap built-in data required during application startup."""

    @classmethod
    def bootstrap_all(cls) -> None:
        """Bootstrap all built-in resources with a dedicated database session."""
        db = SessionLocal()
        try:
            SkillBootstrapService.bootstrap_builtin_skills(db)
            McpServerBootstrapService.bootstrap_builtin_servers(db)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("lifecycle_bootstrap_failed")
            raise
        finally:
            db.close()
