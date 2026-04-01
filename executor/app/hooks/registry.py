import logging
from typing import Any

from app.hooks.base import AgentHook
from app.hooks.factory import HookDependencies, HookFactory

logger = logging.getLogger(__name__)

_HOOK_PHASE_ORDER = {
    "setup": 0,
    "pre_query": 1,
    "message": 2,
    "error": 3,
    "teardown": 4,
}


class HookRegistry:
    @staticmethod
    def default_specs(*, browser_enabled: bool) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = [
            {
                "key": "workspace",
                "phase": "message",
                "order": 10,
                "enabled": True,
            },
            {
                "key": "todo",
                "phase": "message",
                "order": 20,
                "enabled": True,
            },
            {
                "key": "callback",
                "phase": "message",
                "order": 30,
                "enabled": True,
            },
            {
                "key": "run_snapshot",
                "phase": "teardown",
                "order": 100,
                "enabled": True,
            },
        ]
        if browser_enabled:
            specs.append(
                {
                    "key": "browser_screenshot",
                    "phase": "message",
                    "order": 40,
                    "enabled": True,
                }
            )
        return specs

    def build(
        self,
        specs: list[dict[str, Any]],
        dependencies: HookDependencies,
    ) -> list[AgentHook]:
        hooks: list[AgentHook] = []
        sorted_specs = sorted(
            specs,
            key=lambda spec: (
                _HOOK_PHASE_ORDER.get(str(spec.get("phase")), 99),
                int(spec.get("order", 100)),
                str(spec.get("key", "")),
            ),
        )
        for spec in sorted_specs:
            if not isinstance(spec, dict) or spec.get("enabled") is False:
                continue
            key = spec.get("key")
            if not isinstance(key, str) or not key.strip():
                continue
            try:
                hook = HookFactory.create(
                    key.strip(),
                    config=spec.get("config")
                    if isinstance(spec.get("config"), dict)
                    else {},
                    dependencies=dependencies,
                )
            except ValueError:
                logger.warning(
                    "hook_registry_spec_ignored",
                    extra={"hook_key": key.strip()},
                )
                continue
            setattr(hook, "hook_spec", spec)
            hooks.append(hook)
        return hooks
