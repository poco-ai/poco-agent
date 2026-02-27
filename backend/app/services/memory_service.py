from pathlib import Path
from threading import Lock
from typing import Any

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.schemas.memory import MemoryCreateRequest, MemorySearchRequest

try:
    from mem0 import Memory as Mem0Memory
except ImportError:
    Mem0Memory = None


class MemoryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._enabled = self.settings.mem0_enabled
        self._custom_config: dict[str, Any] | None = None
        self._instance: Any | None = None
        self._lock = Lock()

    def is_enabled(self) -> bool:
        return self._enabled

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Memory service is disabled. Set MEM0_ENABLED=true first.",
            )

    def _resolve_openai_api_key(self) -> str:
        api_key = (self.settings.openai_api_key or "").strip()
        if not api_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="OPENAI_API_KEY is required for memory service",
            )
        return api_key

    def _resolve_openai_base_url(self) -> str | None:
        value = (self.settings.openai_base_url or "").strip()
        return value or None

    def _build_graph_store(self) -> dict[str, Any]:
        provider = self.settings.mem0_graph_provider.strip().lower()
        if provider == "memgraph":
            return {
                "provider": "memgraph",
                "config": {
                    "url": self.settings.mem0_memgraph_uri,
                    "username": self.settings.mem0_memgraph_username,
                    "password": self.settings.mem0_memgraph_password,
                },
            }
        if provider != "neo4j":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Unsupported graph provider: {self.settings.mem0_graph_provider}",
            )

        return {
            "provider": "neo4j",
            "config": {
                "url": self.settings.mem0_neo4j_uri,
                "username": self.settings.mem0_neo4j_username,
                "password": self.settings.mem0_neo4j_password,
            },
        }

    def _build_default_config(self) -> dict[str, Any]:
        api_key = self._resolve_openai_api_key()
        openai_base_url = self._resolve_openai_base_url()

        llm_config: dict[str, Any] = {
            "api_key": api_key,
            "model": self.settings.mem0_llm_model,
        }
        embedder_config: dict[str, Any] = {
            "api_key": api_key,
            "model": self.settings.mem0_embedder_model,
        }
        if openai_base_url is not None:
            llm_config["openai_base_url"] = openai_base_url
            embedder_config["openai_base_url"] = openai_base_url

        return {
            "vector_store": {
                "provider": self.settings.mem0_vector_provider,
                "config": {
                    "host": self.settings.mem0_postgres_host,
                    "port": self.settings.mem0_postgres_port,
                    "dbname": self.settings.mem0_postgres_db,
                    "user": self.settings.mem0_postgres_user,
                    "password": self.settings.mem0_postgres_password,
                    "collection_name": self.settings.mem0_postgres_collection_name,
                    "embedding_model_dims": self.settings.mem0_embedding_dims,
                },
            },
            "graph_store": self._build_graph_store(),
            "llm": {
                "provider": "openai",
                "config": llm_config,
            },
            "embedder": {
                "provider": "openai",
                "config": embedder_config,
            },
            "history_db_path": self.settings.mem0_history_db_path,
        }

    @staticmethod
    def _ensure_history_db_parent(config: dict[str, Any]) -> None:
        history_db_path = config.get("history_db_path")
        if not isinstance(history_db_path, str):
            return

        path = history_db_path.strip()
        if not path:
            return

        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_openai_config(config: dict[str, Any]) -> None:
        llm = config.get("llm", {})
        if isinstance(llm, dict) and llm.get("provider") == "openai":
            llm_cfg = llm.get("config", {})
            if (
                not isinstance(llm_cfg, dict)
                or not str(llm_cfg.get("api_key", "")).strip()
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="llm.config.api_key is required when llm.provider is openai",
                )

        embedder = config.get("embedder", {})
        if isinstance(embedder, dict) and embedder.get("provider") == "openai":
            embedder_cfg = embedder.get("config", {})
            if (
                not isinstance(embedder_cfg, dict)
                or not str(embedder_cfg.get("api_key", "")).strip()
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="embedder.config.api_key is required when embedder.provider is openai",
                )

    def _create_instance(self, config: dict[str, Any]) -> Any:
        if Mem0Memory is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="mem0ai dependency is missing. Please install mem0ai first.",
            )

        self._validate_openai_config(config)
        self._ensure_history_db_parent(config)
        return Mem0Memory.from_config(config)

    def _get_instance(self) -> Any:
        with self._lock:
            self._ensure_enabled()
            if self._instance is None:
                config = self._custom_config or self._build_default_config()
                self._instance = self._create_instance(config)
            return self._instance

    @staticmethod
    def _build_scope(
        *,
        user_id: str | None,
        agent_id: str | None,
        run_id: str | None,
        require_identifier: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if user_id:
            params["user_id"] = user_id
        if agent_id:
            params["agent_id"] = agent_id
        if run_id:
            params["run_id"] = run_id
        if require_identifier and not params:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="At least one identifier is required (user_id, agent_id, run_id)",
            )
        return params

    def configure(
        self,
        *,
        enabled: bool | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            if enabled is not None:
                self._enabled = enabled
            if config is not None:
                self._custom_config = config
            self._instance = None

    def create_memories(self, *, user_id: str, request: MemoryCreateRequest) -> Any:
        params = self._build_scope(
            user_id=user_id,
            agent_id=request.agent_id,
            run_id=request.run_id,
        )
        if request.metadata is not None:
            params["metadata"] = request.metadata
        messages = [message.model_dump() for message in request.messages]
        return self._get_instance().add(messages=messages, **params)

    def list_memories(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        params = self._build_scope(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
        )
        return self._get_instance().get_all(**params)

    def get_memory(self, memory_id: str) -> Any:
        return self._get_instance().get(memory_id)

    def search_memories(self, *, user_id: str, request: MemorySearchRequest) -> Any:
        params: dict[str, Any] = self._build_scope(
            user_id=user_id,
            agent_id=request.agent_id,
            run_id=request.run_id,
        )
        if request.filters is not None:
            params["filters"] = request.filters
        return self._get_instance().search(query=request.query, **params)

    def update_memory(self, *, memory_id: str, data: dict[str, Any]) -> Any:
        return self._get_instance().update(memory_id=memory_id, data=data)

    def get_memory_history(self, *, memory_id: str) -> Any:
        return self._get_instance().history(memory_id=memory_id)

    def delete_memory(self, *, memory_id: str) -> None:
        self._get_instance().delete(memory_id=memory_id)

    def delete_all_memories(
        self,
        *,
        user_id: str,
        agent_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        params = self._build_scope(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
        )
        self._get_instance().delete_all(**params)

    def reset(self) -> None:
        self._get_instance().reset()
