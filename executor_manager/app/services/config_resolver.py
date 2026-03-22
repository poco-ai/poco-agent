import logging
import re
import time
from typing import Any, TypedDict
from urllib.parse import urlparse

from app.core.settings import get_settings
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.backend_client import BackendClient


_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
logger = logging.getLogger(__name__)
_GITHUB_HOSTS = {"github.com", "www.github.com"}


class ProviderRuntimeSpec(TypedDict):
    source_api_key_env_keys: tuple[str, ...]
    source_base_url_env_keys: tuple[str, ...]
    source_api_key_settings_fields: tuple[str, ...]
    source_base_url_settings_fields: tuple[str, ...]
    default_base_url: str
    runtime_api_key_env_key: str
    runtime_base_url_env_key: str


_PROVIDER_RUNTIME_SPECS: dict[str, ProviderRuntimeSpec] = {
    "anthropic": {
        "source_api_key_env_keys": ("ANTHROPIC_API_KEY",),
        "source_base_url_env_keys": ("ANTHROPIC_BASE_URL",),
        "source_api_key_settings_fields": ("anthropic_api_key",),
        "source_base_url_settings_fields": ("anthropic_base_url",),
        "default_base_url": "https://api.anthropic.com",
        "runtime_api_key_env_key": "ANTHROPIC_API_KEY",
        "runtime_base_url_env_key": "ANTHROPIC_BASE_URL",
    },
    "glm": {
        "source_api_key_env_keys": ("GLM_API_KEY",),
        "source_base_url_env_keys": ("GLM_BASE_URL",),
        "source_api_key_settings_fields": ("glm_api_key",),
        "source_base_url_settings_fields": ("glm_base_url",),
        "default_base_url": "https://open.bigmodel.cn/api/anthropic",
        "runtime_api_key_env_key": "ANTHROPIC_API_KEY",
        "runtime_base_url_env_key": "ANTHROPIC_BASE_URL",
    },
    "minimax": {
        "source_api_key_env_keys": ("MINIMAX_API_KEY",),
        "source_base_url_env_keys": ("MINIMAX_BASE_URL",),
        "source_api_key_settings_fields": ("minimax_api_key",),
        "source_base_url_settings_fields": ("minimax_base_url",),
        "default_base_url": "https://api.minimaxi.com/anthropic",
        "runtime_api_key_env_key": "ANTHROPIC_API_KEY",
        "runtime_base_url_env_key": "ANTHROPIC_BASE_URL",
    },
    "deepseek": {
        "source_api_key_env_keys": ("DEEPSEEK_API_KEY",),
        "source_base_url_env_keys": ("DEEPSEEK_BASE_URL",),
        "source_api_key_settings_fields": ("deepseek_api_key",),
        "source_base_url_settings_fields": ("deepseek_base_url",),
        "default_base_url": "https://api.deepseek.com/anthropic",
        "runtime_api_key_env_key": "ANTHROPIC_API_KEY",
        "runtime_base_url_env_key": "ANTHROPIC_BASE_URL",
    },
}


def _resolve_env_value(value: Any, env_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        matches = _ENV_PATTERN.findall(value)
        if not matches:
            return value
        resolved = value
        for token in matches:
            if token.startswith("env:"):
                var = token[4:]
                default = None
            else:
                parts = token.split(":-", 1)
                var = parts[0]
                default = parts[1] if len(parts) > 1 else None

            if var in env_map:
                value_str = env_map[var]
            elif default is not None:
                value_str = default
            else:
                raise AppException(
                    error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                    message=f"Env var not found: {var}",
                )

            resolved = resolved.replace(f"${{{token}}}", value_str)
        return resolved
    if isinstance(value, list):
        return [_resolve_env_value(v, env_map) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_env_value(v, env_map) for k, v in value.items()}
    return value


class ConfigResolver:
    def __init__(self, backend_client: BackendClient | None = None) -> None:
        self.backend_client = backend_client or BackendClient()
        self.settings = get_settings()

    async def resolve(
        self,
        user_id: str,
        config_snapshot: dict,
        *,
        session_id: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> dict:
        started = time.perf_counter()
        ctx = {
            "user_id": user_id,
            "session_id": session_id,
            "task_id": task_id,
            "run_id": run_id,
        }

        step_started = time.perf_counter()
        env_map = await self._get_env_map(user_id)
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_env_map",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                **ctx,
            },
        )

        step_started = time.perf_counter()
        mcp_config = await self._resolve_effective_mcp_config(user_id, config_snapshot)
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_mcp_config",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "mcp_servers": len(mcp_config) if isinstance(mcp_config, dict) else 0,
                **ctx,
            },
        )

        step_started = time.perf_counter()
        skill_files = await self._resolve_effective_skill_files(
            user_id, config_snapshot
        )
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_skill_files",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "skills": len(skill_files) if isinstance(skill_files, dict) else 0,
                **ctx,
            },
        )
        input_files = config_snapshot.get("input_files") or []

        step_started = time.perf_counter()
        plugin_files = await self._resolve_effective_plugin_files(
            user_id, config_snapshot
        )
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_plugin_files",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "plugins": len(plugin_files) if isinstance(plugin_files, dict) else 0,
                **ctx,
            },
        )

        step_started = time.perf_counter()
        try:
            resolved_subagents = await self._resolve_effective_subagents(
                user_id, config_snapshot
            )
        except Exception as exc:
            logger.warning(f"Failed to resolve subagents for user {user_id}: {exc}")
            resolved_subagents = {}
        structured_agents = (
            resolved_subagents.get("structured_agents")
            if isinstance(resolved_subagents, dict)
            else None
        )
        raw_agents = (
            resolved_subagents.get("raw_agents")
            if isinstance(resolved_subagents, dict)
            else None
        )
        structured_count = (
            len(structured_agents) if isinstance(structured_agents, dict) else 0
        )
        raw_count = len(raw_agents) if isinstance(raw_agents, dict) else 0
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_subagents",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "subagents_structured": structured_count,
                "subagents_raw": raw_count,
                **ctx,
            },
        )

        step_started = time.perf_counter()
        resolved_mcp = self._resolve_mcp(mcp_config, env_map)
        resolved_skills = self._resolve_skills(skill_files, env_map)
        resolved_plugins = self._resolve_plugins(plugin_files, env_map)
        resolved_inputs = _resolve_env_value(input_files, env_map)
        logger.info(
            "timing",
            extra={
                "step": "config_resolve_render",
                "duration_ms": int((time.perf_counter() - step_started) * 1000),
                "input_files": len(input_files) if isinstance(input_files, list) else 0,
                **ctx,
            },
        )

        resolved = dict(config_snapshot)
        resolved["mcp_config"] = resolved_mcp
        resolved["skill_files"] = resolved_skills
        resolved["plugin_files"] = resolved_plugins
        resolved["input_files"] = resolved_inputs
        if isinstance(structured_agents, dict):
            # Expose as `agents` to match ClaudeAgentOptions (programmatic subagents).
            resolved["agents"] = structured_agents
        if isinstance(raw_agents, dict):
            # Raw markdown agents are staged into the workspace by SubAgentStager.
            resolved["subagent_raw_agents"] = raw_agents
        resolved_git = self._resolve_git_token(resolved, env_map)
        if resolved_git:
            resolved.update(resolved_git)
        env_overrides = self._resolve_model_env_overrides(
            resolved,
            env_map,
            user_id=user_id,
            session_id=session_id,
            run_id=run_id,
        )
        if env_overrides:
            resolved["env_overrides"] = env_overrides

        logger.info(
            "timing",
            extra={
                "step": "config_resolve_total",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                **ctx,
            },
        )
        return resolved

    @staticmethod
    def _resolve_git_token(config_snapshot: dict, env_map: dict[str, str]) -> dict:
        """Resolve git token for private GitHub repos.

        We only store the env var key (git_token_env_key) in persisted snapshots.
        The secret value is resolved here at runtime and passed to the executor.
        """
        token_key = str(config_snapshot.get("git_token_env_key") or "").strip()
        if not token_key:
            return {}

        repo_url = str(config_snapshot.get("repo_url") or "").strip()
        if not repo_url:
            return {}

        try:
            parsed = urlparse(repo_url)
        except Exception:
            return {}

        host = (parsed.netloc or "").strip().lower()
        if parsed.scheme not in ("http", "https") or host not in _GITHUB_HOSTS:
            # Safety: never resolve and forward GitHub token to unknown hosts.
            return {}

        token = env_map.get(token_key)
        if not token:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Env var not found: {token_key} (required for private GitHub repo)",
            )

        return {"git_token": token}

    def _resolve_model_env_overrides(
        self,
        config_snapshot: dict,
        env_map: dict[str, str],
        *,
        user_id: str,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, str]:
        selected_model = str(
            config_snapshot.get("model") or self.settings.default_model or ""
        ).strip()
        explicit_provider_id = str(
            config_snapshot.get("model_provider_id") or ""
        ).strip()
        inferred_provider_id = self._infer_provider_id(selected_model)
        provider_id = explicit_provider_id or inferred_provider_id
        if not provider_id:
            return {}

        spec = _PROVIDER_RUNTIME_SPECS.get(provider_id)
        if not spec and explicit_provider_id and inferred_provider_id:
            provider_id = inferred_provider_id
            spec = _PROVIDER_RUNTIME_SPECS.get(provider_id)
        if not spec:
            return {}

        api_key = self._get_first_env_value(
            env_map, spec["source_api_key_env_keys"]
        ) or self._get_first_settings_value(spec["source_api_key_settings_fields"])
        if not api_key:
            raise AppException(
                error_code=ErrorCode.ENV_VAR_NOT_FOUND,
                message=f"Provider credential not configured for model: {selected_model}",
            )

        base_url = (
            self._get_first_env_value(env_map, spec["source_base_url_env_keys"])
            or self._get_first_settings_value(spec["source_base_url_settings_fields"])
            or spec["default_base_url"]
        )
        return {
            spec["runtime_api_key_env_key"]: api_key,
            spec["runtime_base_url_env_key"]: base_url,
        }

    @staticmethod
    def _infer_provider_id(model_id: str) -> str | None:
        value = (model_id or "").strip()
        if not value:
            return None

        lowered = value.lower()
        if lowered.startswith("claude-"):
            return "anthropic"
        if lowered.startswith("glm-") or value.startswith("GLM-"):
            return "glm"
        if lowered.startswith("minimax-") or value.startswith("MiniMax-"):
            return "minimax"
        if lowered.startswith("deepseek-"):
            return "deepseek"
        return None

    @staticmethod
    def _get_first_env_value(env_map: dict[str, str], env_keys: tuple[str, ...]) -> str:
        for key in env_keys:
            value = (env_map.get(key) or "").strip()
            if value:
                return value
        return ""

    def _get_first_settings_value(self, field_names: tuple[str, ...]) -> str:
        for field_name in field_names:
            value = getattr(self.settings, field_name, None)
            normalized = str(value or "").strip()
            if normalized:
                return normalized
        return ""

    async def _get_env_map(self, user_id: str) -> dict[str, str]:
        return await self.backend_client.get_env_map(user_id=user_id)

    async def _resolve_effective_mcp_config(
        self, user_id: str, config_snapshot: dict
    ) -> dict:
        """Resolve MCP config for execution.

        Priority:
        1) config_snapshot.mcp_server_ids -> fetch full mcp_config via backend internal API
        2) config_snapshot.mcp_config toggles (server_id -> bool) -> fetch via backend internal API
        3) legacy config_snapshot.mcp_config already contains full server configs
        """
        server_ids = self._normalize_ids(config_snapshot.get("mcp_server_ids"))
        if server_ids:
            return await self.backend_client.resolve_mcp_config(
                user_id=user_id, server_ids=server_ids
            )

        mcp_config = config_snapshot.get("mcp_config")
        toggle_ids = self._extract_enabled_ids_from_toggles(mcp_config)
        if toggle_ids is not None:
            return await self.backend_client.resolve_mcp_config(
                user_id=user_id, server_ids=toggle_ids
            )

        return mcp_config if isinstance(mcp_config, dict) else {}

    async def _resolve_effective_skill_files(
        self, user_id: str, config_snapshot: dict
    ) -> dict:
        """Resolve skills for execution.

        Priority:
        1) config_snapshot.skill_ids -> fetch entries via backend internal API
        2) legacy config_snapshot.skill_files already contains entry configs
        """
        if "skill_ids" in config_snapshot:
            skill_ids = self._normalize_ids(config_snapshot.get("skill_ids"))
            return await self.backend_client.resolve_skill_config(
                user_id=user_id, skill_ids=skill_ids
            )

        legacy = config_snapshot.get("skill_files")
        return legacy if isinstance(legacy, dict) else {}

    async def _resolve_effective_plugin_files(
        self, user_id: str, config_snapshot: dict
    ) -> dict:
        """Resolve plugins for execution.

        Priority:
        1) config_snapshot.plugin_ids -> fetch entries via backend internal API
        2) legacy config_snapshot.plugin_files already contains entry configs
        """
        plugin_ids = self._normalize_ids(config_snapshot.get("plugin_ids"))
        if plugin_ids:
            return await self.backend_client.resolve_plugin_config(
                user_id=user_id, plugin_ids=plugin_ids
            )

        legacy = config_snapshot.get("plugin_files")
        return legacy if isinstance(legacy, dict) else {}

    async def _resolve_effective_subagents(
        self, user_id: str, config_snapshot: dict
    ) -> dict:
        subagent_ids: list[int] | None
        if "subagent_ids" not in config_snapshot:
            subagent_ids = None
        else:
            subagent_ids = self._normalize_ids(config_snapshot.get("subagent_ids"))
        return await self.backend_client.resolve_subagents(
            user_id=user_id, subagent_ids=subagent_ids
        )

    @staticmethod
    def _normalize_ids(value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        seen: set[int] = set()
        for item in value:
            sid: int | None = None
            if isinstance(item, int):
                sid = item
            elif isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                try:
                    sid = int(item)
                except ValueError:
                    sid = None
            if sid is None:
                continue
            if sid in seen:
                continue
            seen.add(sid)
            result.append(sid)
        return result

    @staticmethod
    def _extract_enabled_ids_from_toggles(value: Any) -> list[int] | None:
        """Convert {id: bool} toggles into enabled id list.

        Returns None when the value does not look like toggles.
        """
        if not isinstance(value, dict):
            return None
        if not value:
            return []
        ids: list[int] = []
        seen: set[int] = set()
        for key, enabled in value.items():
            if not isinstance(enabled, bool):
                return None
            if enabled is not True:
                continue
            if not isinstance(key, str):
                return None
            key = key.strip()
            if not key:
                continue
            try:
                sid = int(key)
            except ValueError:
                return None
            if sid in seen:
                continue
            seen.add(sid)
            ids.append(sid)
        return ids

    @staticmethod
    def _resolve_mcp(mcp_config: dict, env_map: dict[str, str]) -> dict:
        resolved: dict = {}
        for name, config in mcp_config.items():
            if not isinstance(config, dict):
                resolved[name] = config
                continue
            resolved[name] = _resolve_env_value(config, env_map)
        return resolved

    @staticmethod
    def _resolve_skills(skills: dict, env_map: dict[str, str]) -> dict:
        resolved: dict = {}
        for name, config in (skills or {}).items():
            if not isinstance(config, dict):
                continue
            if config.get("enabled") is False:
                resolved[name] = {"enabled": False}
                continue
            resolved[name] = _resolve_env_value(config, env_map)
        return resolved

    @staticmethod
    def _resolve_plugins(plugins: dict, env_map: dict[str, str]) -> dict:
        resolved: dict = {}
        for name, config in (plugins or {}).items():
            if not isinstance(config, dict):
                continue
            if config.get("enabled") is False:
                resolved[name] = {"enabled": False}
                continue
            resolved[name] = _resolve_env_value(config, env_map)
        return resolved
