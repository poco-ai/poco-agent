import unittest
from unittest.mock import MagicMock

from app.hooks.callback import CallbackHook
from app.hooks.registry import HookDependencies, HookRegistry
from app.hooks.workspace import WorkspaceHook


class TestHookRegistry(unittest.TestCase):
    def test_build_sorts_specs_and_creates_builtin_hooks(self) -> None:
        registry = HookRegistry()
        hooks = registry.build(
            [
                {
                    "key": "callback",
                    "phase": "message",
                    "order": 20,
                    "enabled": True,
                },
                {
                    "key": "workspace",
                    "phase": "message",
                    "order": 10,
                    "enabled": True,
                },
            ],
            HookDependencies(
                callback_client=MagicMock(),
                computer_client=None,
                run_id="run-123",
            ),
        )

        assert len(hooks) == 2
        assert isinstance(hooks[0], WorkspaceHook)
        assert isinstance(hooks[1], CallbackHook)

    def test_build_skips_disabled_specs(self) -> None:
        registry = HookRegistry()
        hooks = registry.build(
            [
                {
                    "key": "workspace",
                    "phase": "message",
                    "order": 10,
                    "enabled": False,
                }
            ],
            HookDependencies(
                callback_client=MagicMock(),
                computer_client=None,
                run_id="run-123",
            ),
        )

        assert hooks == []
