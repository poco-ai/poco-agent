import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.executor_client import ExecutorClient


class TestExecutorClientInit(unittest.TestCase):
    """Test ExecutorClient.__init__."""

    def test_init_loads_settings(self) -> None:
        with patch("app.services.executor_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            client = ExecutorClient()
            assert client.settings is not None


class TestExecutorClientTraceHeaders(unittest.TestCase):
    """Test ExecutorClient._trace_headers."""

    def test_trace_headers_with_existing_ids(self) -> None:
        with patch("app.services.executor_client.get_request_id") as mock_get_req:
            with patch("app.services.executor_client.get_trace_id") as mock_get_trace:
                mock_get_req.return_value = "req-123"
                mock_get_trace.return_value = "trace-456"

                headers = ExecutorClient._trace_headers()

                assert headers["X-Request-ID"] == "req-123"
                assert headers["X-Trace-ID"] == "trace-456"

    def test_trace_headers_generates_ids(self) -> None:
        with patch("app.services.executor_client.get_request_id") as mock_get_req:
            with patch("app.services.executor_client.get_trace_id") as mock_get_trace:
                with patch(
                    "app.services.executor_client.generate_request_id"
                ) as mock_gen_req:
                    with patch(
                        "app.services.executor_client.generate_trace_id"
                    ) as mock_gen_trace:
                        mock_get_req.return_value = None
                        mock_get_trace.return_value = None
                        mock_gen_req.return_value = "new-req-123"
                        mock_gen_trace.return_value = "new-trace-456"

                        headers = ExecutorClient._trace_headers()

                        assert headers["X-Request-ID"] == "new-req-123"
                        assert headers["X-Trace-ID"] == "new-trace-456"


@pytest.mark.asyncio
class TestExecutorClientExecuteTask:
    """Test ExecutorClient.execute_task."""

    async def test_execute_task_success(self) -> None:
        with patch("app.services.executor_client.get_settings"):
            client = ExecutorClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"session_id": "session-123"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await client.execute_task(
                    executor_url="http://executor:8080",
                    session_id="session-123",
                    run_id="run-456",
                    prompt="Hello",
                    callback_url="http://callback",
                    callback_token="token-abc",
                    config={"model": "claude"},
                )

                assert result == "session-123"
                mock_client.post.assert_called_once()

    async def test_execute_task_with_optional_params(self) -> None:
        with patch("app.services.executor_client.get_settings"):
            client = ExecutorClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"session_id": "session-123"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await client.execute_task(
                    executor_url="http://executor:8080",
                    session_id="session-123",
                    run_id=None,
                    prompt="Hello",
                    callback_url="http://callback",
                    callback_token="token-abc",
                    config={"model": "claude"},
                    callback_base_url="http://base",
                    sdk_session_id="sdk-789",
                    permission_mode="acceptEdits",
                )

                assert result == "session-123"
                call_args = mock_client.post.call_args
                json_body = call_args.kwargs["json"]
                assert json_body["callback_base_url"] == "http://base"
                assert json_body["sdk_session_id"] == "sdk-789"
                assert json_body["permission_mode"] == "acceptEdits"

    async def test_execute_task_http_error(self) -> None:
        with patch("app.services.executor_client.get_settings"):
            client = ExecutorClient()

            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                with pytest.raises(httpx.HTTPStatusError):
                    await client.execute_task(
                        executor_url="http://executor:8080",
                        session_id="session-123",
                        run_id=None,
                        prompt="Hello",
                        callback_url="http://callback",
                        callback_token="token-abc",
                        config={},
                    )


if __name__ == "__main__":
    unittest.main()
