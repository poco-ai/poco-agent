import httpx

from app.core.settings import get_settings


class ExecutorManagerClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = (settings.executor_manager_url or "").rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0),
            trust_env=False,
        )

    def delete_container(self, container_id: str) -> None:
        self._client.post(
            "/api/v1/executor/delete",
            json={"container_id": container_id, "reason": "Agent assignment release"},
        ).raise_for_status()
