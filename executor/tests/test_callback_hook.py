import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.callback import CallbackAuthenticationError
from app.hooks.base import ExecutionContext
from app.hooks.callback import CallbackHook


class TestCallbackHook(unittest.IsolatedAsyncioTestCase):
    async def test_on_agent_response_propagates_auth_failures(self) -> None:
        """Auth failures should be explicit and stop execution flow."""
        client = MagicMock()
        client.send = AsyncMock(side_effect=CallbackAuthenticationError("bad token"))
        hook = CallbackHook(client=client)
        context = ExecutionContext(session_id="session-123", cwd="/workspace")

        with self.assertRaises(CallbackAuthenticationError):
            await hook.on_agent_response(context, message="hello")

    async def test_on_teardown_skips_send_after_auth_failure(self) -> None:
        """Terminal callback should be skipped when auth is already known broken."""
        client = MagicMock()
        client.send = AsyncMock(return_value=True)
        hook = CallbackHook(client=client)
        hook.execution_error = CallbackAuthenticationError("bad token")
        context = ExecutionContext(session_id="session-123", cwd="/workspace")

        await hook.on_teardown(context)

        client.send.assert_not_awaited()

    async def test_on_teardown_does_not_raise_when_terminal_delivery_fails(self) -> None:
        """Teardown should remain safe even if terminal callback fails to deliver."""
        client = MagicMock()
        client.send = AsyncMock(return_value=False)
        hook = CallbackHook(client=client)
        context = ExecutionContext(session_id="session-123", cwd="/workspace")

        await hook.on_teardown(context)

        client.send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
