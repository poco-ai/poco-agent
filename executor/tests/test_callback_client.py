import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.core.callback import CallbackClient, CallbackAuthenticationError
from app.schemas.callback import AgentCallbackRequest
from app.schemas.enums import CallbackStatus


class TestCallbackClient(unittest.IsolatedAsyncioTestCase):
    """Test executor callback delivery behavior."""

    @staticmethod
    def _create_report() -> AgentCallbackRequest:
        return AgentCallbackRequest(
            session_id="session-123",
            run_id="run-456",
            status=CallbackStatus.RUNNING,
            progress=50,
        )

    async def test_send_includes_authorization_header(self) -> None:
        """Test callback requests always include bearer auth."""
        response = MagicMock()
        response.is_success = True
        response.status_code = 200

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=response)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.core.callback.httpx.AsyncClient", return_value=async_client),
            patch("app.core.callback.get_request_id", return_value="req-1"),
            patch("app.core.callback.get_trace_id", return_value="trace-1"),
        ):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
            )

            result = await client.send(self._create_report())

            assert result is True
            headers = http_client.post.await_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer callback-token"
            assert headers["X-Request-ID"] == "req-1"
            assert headers["X-Trace-ID"] == "trace-1"

    async def test_send_retries_request_errors_before_succeeding(self) -> None:
        """Test request errors are retried with backoff."""
        success_response = MagicMock()
        success_response.is_success = True
        success_response.status_code = 200

        http_client = MagicMock()
        http_client.post = AsyncMock(
            side_effect=[
                httpx.RequestError("temporary failure"),
                success_response,
            ]
        )

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.core.callback.httpx.AsyncClient", return_value=async_client),
            patch("app.core.callback.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        ):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
                max_retries=2,
            )

            result = await client.send(self._create_report())

            assert result is True
            assert http_client.post.await_count == 2
            mock_sleep.assert_awaited_once()

    async def test_send_retries_bounded_times_for_server_errors(self) -> None:
        """Test retriable HTTP failures are retried a bounded number of times."""
        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 503

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=error_response)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.core.callback.httpx.AsyncClient", return_value=async_client),
            patch("app.core.callback.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        ):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
                max_retries=2,
            )

            result = await client.send(self._create_report())

            assert result is False
            assert http_client.post.await_count == 3
            assert mock_sleep.await_count == 2

    async def test_send_does_not_retry_non_retriable_http_failures(self) -> None:
        """Test auth failures fail fast without retrying."""
        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 403

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=error_response)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.core.callback.httpx.AsyncClient", return_value=async_client),
            patch("app.core.callback.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        ):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
                max_retries=3,
            )

            with self.assertRaises(CallbackAuthenticationError):
                await client.send(self._create_report())
            assert http_client.post.await_count == 1
            mock_sleep.assert_not_awaited()

    async def test_send_raises_on_unauthorized_status(self) -> None:
        """401 responses should be treated as auth failures."""
        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 401

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=error_response)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.callback.httpx.AsyncClient", return_value=async_client):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
            )

            with self.assertRaises(CallbackAuthenticationError):
                await client.send(self._create_report())

    async def test_validate_auth_raises_for_invalid_token(self) -> None:
        """Test auth probe fails closed on callback token mismatch."""
        auth_failure = MagicMock()
        auth_failure.status_code = 403
        auth_failure.is_success = False

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=auth_failure)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.callback.httpx.AsyncClient", return_value=async_client):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="bad-token",
            )

            with self.assertRaises(CallbackAuthenticationError):
                await client.validate_auth()

    async def test_validate_auth_raises_on_unauthorized(self) -> None:
        """401 auth probe responses should fail closed."""
        auth_failure = MagicMock()
        auth_failure.status_code = 401
        auth_failure.is_success = False

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=auth_failure)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.callback.httpx.AsyncClient", return_value=async_client):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="bad-token",
            )

            with self.assertRaises(CallbackAuthenticationError):
                await client.validate_auth()

    async def test_validate_auth_accepts_validation_error_status(self) -> None:
        """Test auth probe accepts FastAPI validation responses."""
        validation_error = MagicMock()
        validation_error.status_code = 422
        validation_error.is_success = False

        http_client = MagicMock()
        http_client.post = AsyncMock(return_value=validation_error)

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=http_client)
        async_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.core.callback.httpx.AsyncClient", return_value=async_client):
            client = CallbackClient(
                callback_url="http://callback.local/api/v1/callback",
                callback_token="callback-token",
            )

            await client.validate_auth()


if __name__ == "__main__":
    unittest.main()
