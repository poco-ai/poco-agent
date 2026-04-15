from typing import Any

from app.services.backend_client import BackendClient


class PresetResolver:
    def __init__(self, backend_client: BackendClient | None = None) -> None:
        self.backend_client = backend_client or BackendClient()

    async def resolve_preset_config(
        self, user_id: str, preset_id: int
    ) -> dict[str, Any]:
        preset = await self.backend_client.get_preset(
            user_id=user_id, preset_id=preset_id
        )
        if not preset:
            return {}
        return {
            "preset_id": preset.get("preset_id"),
            "prompt_template": preset.get("prompt_template"),
            "browser_enabled": bool(preset.get("browser_enabled")),
            "memory_enabled": bool(preset.get("memory_enabled")),
            "container_mode": preset.get("container_mode") or "ephemeral",
            "skill_ids": self._normalize_int_list(preset.get("skill_ids")),
            "mcp_server_ids": self._normalize_int_list(preset.get("mcp_server_ids")),
            "plugin_ids": self._normalize_int_list(preset.get("plugin_ids")),
            "subagent_configs": self._normalize_subagent_configs(
                preset.get("subagent_configs")
            ),
        }

    async def apply_preset_config(
        self,
        *,
        user_id: str,
        config_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        preset_id = config_snapshot.get("preset_id")
        if not isinstance(preset_id, int) or preset_id <= 0:
            return dict(config_snapshot)
        preset_config = await self.resolve_preset_config(user_id, preset_id)
        return self.merge_with_manual_config(preset_config, config_snapshot)

    def merge_with_manual_config(
        self,
        preset_config: dict[str, Any],
        manual_config: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(preset_config)
        manual = dict(manual_config)

        for field_name in ("skill_ids", "mcp_server_ids", "plugin_ids", "subagent_ids"):
            merged[field_name] = self._merge_int_lists(
                preset_config.get(field_name),
                manual.get(field_name),
            )

        merged["subagent_configs"] = self._merge_subagent_configs(
            preset_config.get("subagent_configs"),
            manual.get("subagent_configs"),
        )

        if "local_mounts" in manual:
            merged["local_mounts"] = manual.get("local_mounts") or []

        for key, value in manual.items():
            if key in {
                "skill_ids",
                "mcp_server_ids",
                "plugin_ids",
                "subagent_ids",
                "subagent_configs",
                "local_mounts",
            }:
                continue
            if value is None:
                continue
            merged[key] = value

        return merged

    @staticmethod
    def _normalize_int_list(value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        seen: set[int] = set()
        for item in value:
            if not isinstance(item, int):
                continue
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    @staticmethod
    def _merge_int_lists(base: Any, override: Any) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for source in (base, override):
            if not isinstance(source, list):
                continue
            for item in source:
                if not isinstance(item, int):
                    continue
                if item in seen:
                    continue
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _normalize_subagent_configs(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(
                {
                    "name": name,
                    "description": item.get("description"),
                    "prompt": item.get("prompt"),
                    "model": item.get("model"),
                    "tools": item.get("tools"),
                }
            )
        return result

    def _merge_subagent_configs(self, base: Any, override: Any) -> list[dict[str, Any]]:
        merged_by_name: dict[str, dict[str, Any]] = {}
        ordered_names: list[str] = []
        for source in (
            self._normalize_subagent_configs(base),
            self._normalize_subagent_configs(override),
        ):
            for item in source:
                name = item["name"]
                if name not in merged_by_name:
                    ordered_names.append(name)
                    merged_by_name[name] = item
                    continue
                merged_by_name[name] = {**merged_by_name[name], **item}
        return [merged_by_name[name] for name in ordered_names]
