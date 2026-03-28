from app.services.container_pool import ContainerPool
import logging

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Shared runtime helpers for the queue-driven dispatch path.

    Direct task dispatch now flows through Backend's run queue and
    `RunPullService`. This class intentionally retains only container-pool
    helper methods that are shared by the active runtime path and executor APIs.
    """

    container_pool: ContainerPool | None = None

    @classmethod
    def get_container_pool(cls) -> ContainerPool:
        """Get container pool instance (lazy load)."""
        if cls.container_pool is None:
            cls.container_pool = ContainerPool()
        return cls.container_pool

    @classmethod
    async def resolve_executor_target(
        cls,
        *,
        session_id: str,
        user_id: str,
        browser_enabled: bool,
        container_mode: str,
        container_id: str | None,
    ) -> tuple[str, str | None]:
        container_pool = cls.get_container_pool()
        return await container_pool.get_or_create_container(
            session_id=session_id,
            user_id=user_id,
            browser_enabled=browser_enabled,
            container_mode=container_mode,
            container_id=container_id,
        )

    @staticmethod
    async def on_task_complete(session_id: str) -> None:
        """Handle task completion.

        Args:
            session_id: Session ID
        """
        container_pool = TaskDispatcher.get_container_pool()
        await container_pool.on_task_complete(session_id)
