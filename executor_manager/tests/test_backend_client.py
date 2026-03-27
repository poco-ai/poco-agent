import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.backend_client import BackendClient


class TestBackendClientTraceHeaders(unittest.TestCase):
    """Test BackendClient._trace_headers."""

    def test_trace_headers_with_existing_ids(self) -> None:
        with patch("app.services.backend_client.get_request_id") as mock_get_req:
            with patch("app.services.backend_client.get_trace_id") as mock_get_trace:
                mock_get_req.return_value = "req-123"
                mock_get_trace.return_value = "trace-456"

                headers = BackendClient._trace_headers()

                assert headers["X-Request-ID"] == "req-123"
                assert headers["X-Trace-ID"] == "trace-456"

    def test_trace_headers_generates_ids(self) -> None:
        with patch("app.services.backend_client.get_request_id") as mock_get_req:
            with patch("app.services.backend_client.get_trace_id") as mock_get_trace:
                with patch(
                    "app.services.backend_client.generate_request_id"
                ) as mock_gen_req:
                    with patch(
                        "app.services.backend_client.generate_trace_id"
                    ) as mock_gen_trace:
                        mock_get_req.return_value = None
                        mock_get_trace.return_value = None
                        mock_gen_req.return_value = "new-req-123"
                        mock_gen_trace.return_value = "new-trace-456"

                        headers = BackendClient._trace_headers()

                        assert headers["X-Request-ID"] == "new-req-123"
                        assert headers["X-Trace-ID"] == "new-trace-456"


@pytest.mark.asyncio
class TestBackendClientRequest:
    """Test BackendClient._request method."""

    async def test_request_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client._request("GET", "/test")

                assert result == mock_response

    async def test_request_retries_connect_error(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            call_count = 0

            async def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise httpx.ConnectError("connection error")
                return mock_response

            with patch.object(client._client, "request", side_effect=side_effect):
                result = await client._request("GET", "/test", retry_connect_errors=2)

                assert result == mock_response
                assert call_count == 3

    async def test_request_raises_after_max_retries(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            async def always_fail(*args, **kwargs):
                raise httpx.ConnectError("connection error")

            with patch.object(client._client, "request", side_effect=always_fail):
                with pytest.raises(httpx.ConnectError):
                    await client._request("GET", "/test", retry_connect_errors=2)

    async def test_request_raises_connect_timeout(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            async def timeout_error(*args, **kwargs):
                raise httpx.ConnectTimeout("timeout")

            with patch.object(client._client, "request", side_effect=timeout_error):
                with pytest.raises(httpx.ConnectTimeout):
                    await client._request("GET", "/test")

    async def test_request_raises_http_status_error(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.status_code = 404

            async def raise_404(*args, **kwargs):
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Not found", request=MagicMock(), response=mock_response
                )
                return mock_response

            with patch.object(client._client, "request", side_effect=raise_404):
                with pytest.raises(httpx.HTTPStatusError):
                    await client._request("GET", "/test")


@pytest.mark.asyncio
class TestBackendClientCreateSession:
    """Test BackendClient.create_session."""

    async def test_create_session_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"session_id": "sess-123", "sdk_session_id": "sdk-456"}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.create_session("user-123", {"model": "claude"})

                assert result["session_id"] == "sess-123"


@pytest.mark.asyncio
class TestBackendClientUpdateSessionStatus:
    """Test BackendClient.update_session_status."""

    async def test_update_session_status_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                # Should not raise
                await client.update_session_status("sess-123", "completed")


@pytest.mark.asyncio
class TestBackendClientForwardCallback:
    """Test BackendClient.forward_callback."""

    async def test_forward_callback_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"status": "ok"}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.forward_callback({"event": "completed"})

                assert result == {"status": "ok"}

    async def test_forward_callback_empty_data(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.forward_callback({"event": "completed"})

                assert result == {}


@pytest.mark.asyncio
class TestBackendClientClaimRun:
    """Test BackendClient.claim_run."""

    async def test_claim_run_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"run_id": "run-123"}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.claim_run("worker-1", lease_seconds=60)

                assert result["run_id"] == "run-123"

    async def test_claim_run_with_schedule_modes(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": None}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ) as mock_request:
                await client.claim_run(
                    "worker-1", schedule_modes=["immediate", "scheduled"]
                )

                # Verify schedule_modes was included in payload
                call_args = mock_request.call_args
                assert "schedule_modes" in call_args.kwargs["json"]

    async def test_claim_run_returns_none(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": None}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.claim_run("worker-1")

                assert result is None


@pytest.mark.asyncio
class TestBackendClientRunOperations:
    """Test BackendClient run operations: start_run, fail_run."""

    async def test_start_run_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"status": "running"}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.start_run("run-123", "worker-1")

                assert result["status"] == "running"

    async def test_fail_run_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(backend_url="http://backend")

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"status": "failed"}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.fail_run(
                    "run-123", "worker-1", error_message="Something went wrong"
                )

                assert result["status"] == "failed"


@pytest.mark.asyncio
class TestBackendClientEnvMap:
    """Test BackendClient.get_env_map."""

    async def test_get_env_map_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"API_KEY": "secret", "BASE_URL": "https://api.example.com"}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.get_env_map("user-123")

                assert result["API_KEY"] == "secret"


@pytest.mark.asyncio
class TestBackendClientResolveMcpConfig:
    """Test BackendClient.resolve_mcp_config."""

    async def test_resolve_mcp_config_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"server1": {"command": "uvx", "args": ["mcp-server"]}}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.resolve_mcp_config("user-123", [1, 2])

                assert "server1" in result


@pytest.mark.asyncio
class TestBackendClientResolveSkillConfig:
    """Test BackendClient.resolve_skill_config."""

    async def test_resolve_skill_config_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"skill1": {"content": "# Skill content"}}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.resolve_skill_config("user-123", [1])

                assert "skill1" in result


@pytest.mark.asyncio
class TestBackendClientResolveSubagents:
    """Test BackendClient.resolve_subagents."""

    async def test_resolve_subagents_with_ids(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"subagent1": {"name": "researcher"}}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ) as mock_request:
                await client.resolve_subagents("user-123", [1, 2])

                # Verify subagent_ids was included
                call_args = mock_request.call_args
                assert "subagent_ids" in call_args.kwargs["json"]

    async def test_resolve_subagents_none_ids(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ) as mock_request:
                await client.resolve_subagents("user-123", None)

                # Verify subagent_ids was NOT included when None
                call_args = mock_request.call_args
                assert "subagent_ids" not in call_args.kwargs["json"]


@pytest.mark.asyncio
class TestBackendClientResolveSlashCommands:
    """Test BackendClient.resolve_slash_commands."""

    async def test_resolve_slash_commands_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"/help": "Help content", "/review": "Review content"}
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.resolve_slash_commands("user-123")

                assert "/help" in result
                assert "/review" in result

    async def test_resolve_slash_commands_non_dict_response(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "not a dict"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.resolve_slash_commands("user-123")

                assert result == {}


@pytest.mark.asyncio
class TestBackendClientDispatchScheduledTasks:
    """Test BackendClient.dispatch_due_scheduled_tasks."""

    async def test_dispatch_due_scheduled_tasks_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"dispatched": 5}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.dispatch_due_scheduled_tasks(limit=100)

                assert result["dispatched"] == 5


@pytest.mark.asyncio
class TestBackendClientResolvePluginConfig:
    """Test BackendClient.resolve_plugin_config."""

    async def test_resolve_plugin_config_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"plugin1": {"enabled": True}}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ):
                result = await client.resolve_plugin_config("user-123", [1, 2])

                assert "plugin1" in result


@pytest.mark.asyncio
class TestBackendClientGetClaudeMd:
    """Test BackendClient.get_claude_md."""

    async def test_get_claude_md_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"content": "# Claude MD"}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_async_client_cls.return_value = mock_instance

                result = await client.get_claude_md("user-123")

                assert result["content"] == "# Claude MD"

    async def test_get_claude_md_non_dict_response(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "not a dict"}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_async_client_cls.return_value = mock_instance

                result = await client.get_claude_md("user-123")

                assert result == {}


@pytest.mark.asyncio
class TestBackendClientUserInputRequests:
    """Test BackendClient user input request methods."""

    async def test_create_user_input_request_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"id": "req-123"}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_async_client_cls.return_value = mock_instance

                result = await client.create_user_input_request({"question": "ok?"})

                assert result["id"] == "req-123"

    async def test_get_user_input_request_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"status": "pending"}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_instance = AsyncMock()
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_async_client_cls.return_value = mock_instance

                result = await client.get_user_input_request("req-123")

                assert result["status"] == "pending"


@pytest.mark.asyncio
class TestBackendClientMemoryOperations:
    """Test BackendClient memory CRUD operations."""

    def _make_async_client_mock(self, response: MagicMock) -> MagicMock:
        """Helper to create a mocked httpx.AsyncClient context manager."""
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.post = AsyncMock(return_value=response)
        mock_instance.get = AsyncMock(return_value=response)
        mock_instance.put = AsyncMock(return_value=response)
        mock_instance.delete = AsyncMock(return_value=response)
        return mock_instance

    async def test_create_memory_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"id": "mem-123"}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.create_memory("sess-123", {"content": "test"})

                assert result["id"] == "mem-123"

    async def test_get_memory_create_job_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"status": "completed"}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.get_memory_create_job("sess-123", "job-456")

                assert result["status"] == "completed"

    async def test_list_memories_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"id": "mem-1"}, {"id": "mem-2"}]
            }
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.list_memories("sess-123")

                assert len(result) == 2

    async def test_search_memories_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"id": "mem-1"}]}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.search_memories("sess-123", {"query": "test"})

                assert len(result) == 1

    async def test_get_memory_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"id": "mem-123", "content": "test"}
            }
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.get_memory("sess-123", "mem-123")

                assert result["id"] == "mem-123"

    async def test_update_memory_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {"id": "mem-123", "updated": True}
            }
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.update_memory(
                    "sess-123", "mem-123", {"content": "updated"}
                )

                assert result["updated"] is True

    async def test_get_memory_history_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"version": 1}, {"version": 2}]}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.get_memory_history("sess-123", "mem-123")

                assert len(result) == 2

    async def test_delete_memory_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"deleted": True}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.delete_memory("sess-123", "mem-123")

                assert result["deleted"] is True

    async def test_delete_memory_non_dict_response(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": None}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.delete_memory("sess-123", "mem-123")

                assert result == {}

    async def test_delete_all_memories_success(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"count": 5}}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.delete_all_memories("sess-123")

                assert result["count"] == 5

    async def test_delete_all_memories_non_dict_response(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "deleted"}
            mock_response.raise_for_status = MagicMock()

            with patch(
                "app.services.backend_client.httpx.AsyncClient"
            ) as mock_async_client_cls:
                mock_async_client_cls.return_value = self._make_async_client_mock(
                    mock_response
                )

                result = await client.delete_all_memories("sess-123")

                assert result == {}


@pytest.mark.asyncio
class TestBackendClientResolveSlashCommandsWithSkillNames:
    """Test BackendClient.resolve_slash_commands with skill_names parameter."""

    async def test_resolve_slash_commands_with_skill_names(self) -> None:
        with patch("app.services.backend_client.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.backend_url = "http://backend"
            mock_settings_obj.internal_api_token = "token-123"
            mock_settings.return_value = mock_settings_obj

            client = BackendClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"/skill1": "Skill content"}}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "request", AsyncMock(return_value=mock_response)
            ) as mock_request:
                result = await client.resolve_slash_commands(
                    "user-123", skill_names=["skill1"]
                )

                # Verify skill_names was included in payload
                call_args = mock_request.call_args
                assert "skill_names" in call_args.kwargs["json"]
                assert "/skill1" in result


if __name__ == "__main__":
    unittest.main()
