import logging
import time

from app.core.settings import get_settings
from app.services.backend_client import BackendClient

logger = logging.getLogger(__name__)


class AgentAssignmentDispatchService:
    """Background service that asks Backend to trigger due agent assignments."""

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        self.settings = get_settings()
        self.backend_client = backend_client or BackendClient()

    async def dispatch_due(self) -> None:
        started = time.perf_counter()
        batch_size = max(1, int(self.settings.agent_assignments_dispatch_batch_size))
        try:
            payload = await self.backend_client.dispatch_due_agent_assignments(
                limit=batch_size
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "agent_assignments_dispatch",
                extra={
                    "duration_ms": duration_ms,
                    "batch_size": batch_size,
                    "result": payload,
                },
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "agent_assignments_dispatch_failed",
                extra={
                    "duration_ms": duration_ms,
                    "batch_size": batch_size,
                    "error": str(e),
                },
            )
