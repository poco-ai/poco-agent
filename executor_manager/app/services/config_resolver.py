import logging
import re
import time
from typing import Any

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.backend_client import BackendClient


_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
logger = logging.getLogger(__name__)


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
        resolved_mcp = self._resolve_mcp(mcp_config, env_map)
        resolved_skills = self._resolve_skills(skill_files, env_map)
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
        resolved["input_files"] = resolved_inputs

        logger.info(
            "timing",
            extra={
                "step": "config_resolve_total",
                "duration_ms": int((time.perf_counter() - started) * 1000),
                **ctx,
            },
        )
        return resolved

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
        skill_ids = self._normalize_ids(config_snapshot.get("skill_ids"))
        if skill_ids:
            return await self.backend_client.resolve_skill_config(
                user_id=user_id, skill_ids=skill_ids
            )

        legacy = config_snapshot.get("skill_files")
        return legacy if isinstance(legacy, dict) else {}

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
