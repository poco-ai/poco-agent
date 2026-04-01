import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.services.config_resolver import (
    ConfigResolver,
    _resolve_env_value,
)


class TestResolveEnvValue(unittest.TestCase):
    """Test _resolve_env_value function."""

    def test_non_string_value(self) -> None:
        result = _resolve_env_value(123, {})
        assert result == 123

    def test_non_string_bool(self) -> None:
        result = _resolve_env_value(True, {})
        assert result is True

    def test_non_string_none(self) -> None:
        result = _resolve_env_value(None, {})
        assert result is None

    def test_string_without_env_var(self) -> None:
        result = _resolve_env_value("hello world", {})
        assert result == "hello world"

    def test_simple_env_var(self) -> None:
        result = _resolve_env_value("${API_KEY}", {"API_KEY": "secret123"})
        assert result == "secret123"

    def test_env_var_with_default(self) -> None:
        result = _resolve_env_value("${VAR:-default_value}", {})
        assert result == "default_value"

    def test_env_var_with_default_override(self) -> None:
        result = _resolve_env_value("${VAR:-default_value}", {"VAR": "actual_value"})
        assert result == "actual_value"

    def test_env_var_with_env_prefix(self) -> None:
        result = _resolve_env_value("${env:MY_VAR}", {"MY_VAR": "my_value"})
        assert result == "my_value"

    def test_env_var_with_env_prefix_not_found(self) -> None:
        with pytest.raises(AppException) as exc_info:
            _resolve_env_value("${env:MISSING_VAR}", {})
        assert exc_info.value.error_code == ErrorCode.ENV_VAR_NOT_FOUND

    def test_multiple_env_vars(self) -> None:
        result = _resolve_env_value(
            "${HOST}:${PORT}", {"HOST": "localhost", "PORT": "8080"}
        )
        assert result == "localhost:8080"

    def test_env_var_not_found(self) -> None:
        with pytest.raises(AppException) as exc_info:
            _resolve_env_value("${MISSING_VAR}", {})
        assert exc_info.value.error_code == ErrorCode.ENV_VAR_NOT_FOUND
        assert "MISSING_VAR" in exc_info.value.message

    def test_list_values(self) -> None:
        result = _resolve_env_value(
            ["${VAR1}", "${VAR2}", "static"],
            {"VAR1": "value1", "VAR2": "value2"},
        )
        assert result == ["value1", "value2", "static"]

    def test_dict_values(self) -> None:
        result = _resolve_env_value(
            {"key1": "${VAR1}", "key2": "static"},
            {"VAR1": "value1"},
        )
        assert result == {"key1": "value1", "key2": "static"}

    def test_nested_dict_and_list(self) -> None:
        result = _resolve_env_value(
            {"keys": ["${VAR1}", "${VAR2}"], "nested": {"key": "${VAR3}"}},
            {"VAR1": "a", "VAR2": "b", "VAR3": "c"},
        )
        assert result == {"keys": ["a", "b"], "nested": {"key": "c"}}

    def test_env_var_in_middle_of_string(self) -> None:
        result = _resolve_env_value("prefix-${VAR}-suffix", {"VAR": "middle"})
        assert result == "prefix-middle-suffix"

    def test_empty_string(self) -> None:
        result = _resolve_env_value("", {})
        assert result == ""

    def test_empty_env_map(self) -> None:
        with pytest.raises(AppException):
            _resolve_env_value("${VAR}", {})

    def test_env_var_with_empty_value(self) -> None:
        result = _resolve_env_value("${VAR}", {"VAR": ""})
        assert result == ""

    def test_complex_default_value(self) -> None:
        result = _resolve_env_value("${URL:-https://default.example.com}", {})
        assert result == "https://default.example.com"


class TestConfigResolverInit(unittest.TestCase):
    """Test ConfigResolver.__init__."""

    def test_init_with_backend_client(self) -> None:
        mock_client = MagicMock()
        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            resolver = ConfigResolver(backend_client=mock_client)
            assert resolver.backend_client == mock_client

    def test_init_without_backend_client(self) -> None:
        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            with patch("app.services.config_resolver.BackendClient") as mock_bc:
                ConfigResolver()
                mock_bc.assert_called_once()


class TestConfigResolverNormalizeIds(unittest.TestCase):
    """Test ConfigResolver._normalize_ids."""

    def test_empty_list(self) -> None:
        result = ConfigResolver._normalize_ids([])
        assert result == []

    def test_non_list_input(self) -> None:
        result = ConfigResolver._normalize_ids("not a list")
        assert result == []

    def test_int_items(self) -> None:
        result = ConfigResolver._normalize_ids([1, 2, 3])
        assert result == [1, 2, 3]

    def test_string_items(self) -> None:
        result = ConfigResolver._normalize_ids(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_mixed_items(self) -> None:
        result = ConfigResolver._normalize_ids([1, "2", 3])
        assert result == [1, 2, 3]

    def test_duplicate_items(self) -> None:
        result = ConfigResolver._normalize_ids([1, "1", 2, 2])
        assert result == [1, 2]

    def test_invalid_string_items(self) -> None:
        result = ConfigResolver._normalize_ids(["invalid", 1])
        assert result == [1]

    def test_empty_string_items(self) -> None:
        result = ConfigResolver._normalize_ids(["", "  ", 1])
        assert result == [1]

    def test_none_item(self) -> None:
        result = ConfigResolver._normalize_ids([None, 1])  # type: ignore
        assert result == [1]


class TestConfigResolverExtractEnabledIdsFromToggles(unittest.TestCase):
    """Test ConfigResolver._extract_enabled_ids_from_toggles."""

    def test_non_dict_input(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles("not a dict")
        assert result is None

    def test_empty_dict(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles({})
        assert result == []

    def test_valid_toggles(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles(
            {"1": True, "2": False, "3": True}
        )
        assert result == [1, 3]

    def test_non_bool_value(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles(
            {"1": "true"}  # type: ignore
        )
        assert result is None

    def test_non_string_key(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles(
            {1: True}  # type: ignore
        )
        assert result is None

    def test_invalid_key_format(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles({"invalid": True})
        assert result is None

    def test_duplicate_ids(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles(
            {"1": True, " 1 ": True}
        )
        assert result == [1]

    def test_empty_key(self) -> None:
        result = ConfigResolver._extract_enabled_ids_from_toggles({"": True, "1": True})
        assert result == [1]


class TestConfigResolverInferProviderId(unittest.TestCase):
    """Test ConfigResolver._infer_provider_id."""

    def test_claude_model(self) -> None:
        assert ConfigResolver._infer_provider_id("claude-3-opus") == "anthropic"
        assert ConfigResolver._infer_provider_id("CLAUDE-3-sonnet") == "anthropic"

    def test_glm_model(self) -> None:
        assert ConfigResolver._infer_provider_id("glm-4") == "glm"
        assert ConfigResolver._infer_provider_id("GLM-4") == "glm"

    def test_minimax_model(self) -> None:
        assert ConfigResolver._infer_provider_id("minimax-01") == "minimax"
        assert ConfigResolver._infer_provider_id("MiniMax-01") == "minimax"

    def test_deepseek_model(self) -> None:
        assert ConfigResolver._infer_provider_id("deepseek-chat") == "deepseek"

    def test_unknown_model(self) -> None:
        assert ConfigResolver._infer_provider_id("unknown-model") is None

    def test_empty_string(self) -> None:
        assert ConfigResolver._infer_provider_id("") is None

    def test_none_value(self) -> None:
        assert ConfigResolver._infer_provider_id(None) is None  # type: ignore


class TestConfigResolverGetFirstEnvValue(unittest.TestCase):
    """Test ConfigResolver._get_first_env_value."""

    def test_found_first_key(self) -> None:
        result = ConfigResolver._get_first_env_value(
            {"KEY1": "value1", "KEY2": "value2"}, ("KEY1", "KEY2")
        )
        assert result == "value1"

    def test_found_second_key(self) -> None:
        result = ConfigResolver._get_first_env_value(
            {"KEY2": "value2"}, ("KEY1", "KEY2")
        )
        assert result == "value2"

    def test_not_found(self) -> None:
        result = ConfigResolver._get_first_env_value({}, ("KEY1", "KEY2"))
        assert result == ""

    def test_empty_value(self) -> None:
        result = ConfigResolver._get_first_env_value({"KEY1": ""}, ("KEY1", "KEY2"))
        assert result == ""


class TestConfigResolverBuildAnthropicModelAliasOverrides(unittest.TestCase):
    """Test ConfigResolver._build_anthropic_model_alias_overrides."""

    def test_anthropic_provider(self) -> None:
        result = ConfigResolver._build_anthropic_model_alias_overrides(
            provider_id="anthropic", model_id="custom-model"
        )
        assert "ANTHROPIC_MODEL" in result
        assert result["ANTHROPIC_MODEL"] == "custom-model"

    def test_anthropic_authtoken_provider(self) -> None:
        result = ConfigResolver._build_anthropic_model_alias_overrides(
            provider_id="anthropic-authtoken", model_id="custom-model"
        )
        assert "ANTHROPIC_MODEL" in result

    def test_other_provider(self) -> None:
        result = ConfigResolver._build_anthropic_model_alias_overrides(
            provider_id="glm", model_id="glm-4"
        )
        assert result == {}

    def test_claude_prefix_model(self) -> None:
        result = ConfigResolver._build_anthropic_model_alias_overrides(
            provider_id="anthropic", model_id="claude-3-opus"
        )
        assert result == {}

    def test_empty_model_id(self) -> None:
        result = ConfigResolver._build_anthropic_model_alias_overrides(
            provider_id="anthropic", model_id=""
        )
        assert result == {}


class TestConfigResolverResolveGitToken(unittest.TestCase):
    """Test ConfigResolver._resolve_git_token."""

    def test_no_token_key(self) -> None:
        result = ConfigResolver._resolve_git_token({}, {})
        assert result == {}

    def test_empty_token_key(self) -> None:
        result = ConfigResolver._resolve_git_token({"git_token_env_key": ""}, {})
        assert result == {}

    def test_no_repo_url(self) -> None:
        result = ConfigResolver._resolve_git_token(
            {"git_token_env_key": "GITHUB_TOKEN"}, {}
        )
        assert result == {}

    def test_non_github_url(self) -> None:
        result = ConfigResolver._resolve_git_token(
            {
                "git_token_env_key": "GITHUB_TOKEN",
                "repo_url": "https://gitlab.com/user/repo",
            },
            {"GITHUB_TOKEN": "token123"},
        )
        assert result == {}

    def test_github_url_success(self) -> None:
        result = ConfigResolver._resolve_git_token(
            {
                "git_token_env_key": "GITHUB_TOKEN",
                "repo_url": "https://github.com/user/repo",
            },
            {"GITHUB_TOKEN": "token123"},
        )
        assert result == {"git_token": "token123"}

    def test_github_url_missing_token(self) -> None:
        with pytest.raises(AppException) as exc_info:
            ConfigResolver._resolve_git_token(
                {
                    "git_token_env_key": "GITHUB_TOKEN",
                    "repo_url": "https://github.com/user/repo",
                },
                {},
            )
        assert exc_info.value.error_code == ErrorCode.ENV_VAR_NOT_FOUND

    def test_www_github_url(self) -> None:
        result = ConfigResolver._resolve_git_token(
            {
                "git_token_env_key": "GITHUB_TOKEN",
                "repo_url": "https://www.github.com/user/repo",
            },
            {"GITHUB_TOKEN": "token123"},
        )
        assert result == {"git_token": "token123"}

    def test_invalid_url_scheme(self) -> None:
        result = ConfigResolver._resolve_git_token(
            {
                "git_token_env_key": "GITHUB_TOKEN",
                "repo_url": "ftp://github.com/user/repo",
            },
            {"GITHUB_TOKEN": "token123"},
        )
        assert result == {}

    def test_invalid_url_parse(self) -> None:
        """Test that invalid URLs are handled gracefully."""
        result = ConfigResolver._resolve_git_token(
            {
                "git_token_env_key": "GITHUB_TOKEN",
                "repo_url": "not a valid url at all!!!",
            },
            {"GITHUB_TOKEN": "token123"},
        )
        assert result == {}


class TestConfigResolverResolveMcp(unittest.TestCase):
    """Test ConfigResolver._resolve_mcp."""

    def test_resolve_mcp_config(self) -> None:
        mcp_config = {
            "server1": {"command": "${CMD}", "args": ["${ARG}"]},
            "server2": "not a dict",
        }
        env_map = {"CMD": "uvx", "ARG": "mcp-server"}
        result = ConfigResolver._resolve_mcp(mcp_config, env_map)
        assert result["server1"]["command"] == "uvx"
        assert result["server2"] == "not a dict"


class TestConfigResolverResolveSkills(unittest.TestCase):
    """Test ConfigResolver._resolve_skills."""

    def test_resolve_skills(self) -> None:
        skills = {
            "skill1": {"content": "${API_KEY}"},
            "skill2": {"enabled": False},
            "skill3": "not a dict",
        }
        env_map = {"API_KEY": "secret"}
        result = ConfigResolver._resolve_skills(skills, env_map)
        assert result["skill1"]["content"] == "secret"
        assert result["skill2"]["enabled"] is False
        assert "skill3" not in result

    def test_none_skills(self) -> None:
        result = ConfigResolver._resolve_skills(None, {})  # type: ignore
        assert result == {}


class TestConfigResolverResolvePlugins(unittest.TestCase):
    """Test ConfigResolver._resolve_plugins."""

    def test_resolve_plugins(self) -> None:
        plugins = {
            "plugin1": {"config": "${VALUE}"},
            "plugin2": {"enabled": False},
        }
        env_map = {"VALUE": "test"}
        result = ConfigResolver._resolve_plugins(plugins, env_map)
        assert result["plugin1"]["config"] == "test"
        assert result["plugin2"]["enabled"] is False


@pytest.mark.asyncio
class TestConfigResolverExecutionSettings:
    async def test_resolve_includes_user_execution_settings_and_hook_specs(
        self,
    ) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={})
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})
        mock_backend.resolve_skill_config = AsyncMock(return_value={})
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})
        mock_backend.resolve_subagents = AsyncMock(return_value={})
        mock_backend.get_execution_settings = AsyncMock(
            return_value={
                "schema_version": "v1",
                "hooks": {
                    "pipeline": [
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
                    ]
                },
                "workspace": {"checkout_strategy": "worktree"},
            }
        )

        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.default_model = None
            mock_settings.return_value = mock_settings_obj

            resolver = ConfigResolver(backend_client=mock_backend)
            resolver.settings = mock_settings_obj

            result = await resolver.resolve(
                user_id="user-123",
                config_snapshot={},
            )

        mock_backend.get_execution_settings.assert_awaited_once_with("user-123")
        assert result["execution_settings"]["schema_version"] == "v1"
        assert result["workspace_strategy"] == "worktree"
        assert [spec["key"] for spec in result["hook_specs"]] == [
            "workspace",
            "callback",
        ]


class TestConfigResolverResolvePluginsExtended(unittest.TestCase):
    def test_non_dict_config(self) -> None:
        """Test that non-dict plugin configs are skipped."""
        plugins = {
            "plugin1": "not a dict",
            "plugin2": {"config": "value"},
        }
        result = ConfigResolver._resolve_plugins(plugins, {})
        assert "plugin1" not in result
        assert "plugin2" in result


@pytest.mark.asyncio
class TestConfigResolverResolve:
    """Test ConfigResolver.resolve."""

    async def test_resolve_success(self) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={"API_KEY": "secret"})
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})
        mock_backend.resolve_skill_config = AsyncMock(return_value={})
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})
        mock_backend.resolve_subagents = AsyncMock(return_value={})

        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.default_model = "claude-3-opus"
            mock_settings_obj.anthropic_api_key = "test-key"
            mock_settings.return_value = mock_settings_obj

            resolver = ConfigResolver(backend_client=mock_backend)
            resolver.settings = mock_settings_obj

            result = await resolver.resolve(
                user_id="user-123",
                config_snapshot={"model": "claude-3-opus"},
                session_id="session-456",
            )

            assert "mcp_config" in result
            assert "skill_files" in result
            mock_backend.get_env_map.assert_called_once()

    async def test_resolve_with_structured_agents(self) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={})
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})
        mock_backend.resolve_skill_config = AsyncMock(return_value={})
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})
        mock_backend.resolve_subagents = AsyncMock(
            return_value={
                "structured_agents": {"agent1": {"name": "test"}},
                "raw_agents": {"agent2": {"content": "test"}},
            }
        )

        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.default_model = None
            mock_settings.return_value = mock_settings_obj

            resolver = ConfigResolver(backend_client=mock_backend)
            resolver.settings = mock_settings_obj

            result = await resolver.resolve(
                user_id="user-123",
                config_snapshot={},
            )

            assert result["agents"] == {"agent1": {"name": "test"}}
            assert result["subagent_raw_agents"] == {"agent2": {"content": "test"}}

    async def test_resolve_with_git_token(self) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={"GITHUB_TOKEN": "token123"})
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})
        mock_backend.resolve_skill_config = AsyncMock(return_value={})
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})
        mock_backend.resolve_subagents = AsyncMock(return_value={})

        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.default_model = None
            mock_settings.return_value = mock_settings_obj

            resolver = ConfigResolver(backend_client=mock_backend)
            resolver.settings = mock_settings_obj

            result = await resolver.resolve(
                user_id="user-123",
                config_snapshot={
                    "git_token_env_key": "GITHUB_TOKEN",
                    "repo_url": "https://github.com/user/repo",
                },
            )

            assert result["git_token"] == "token123"

    async def test_resolve_with_subagent_exception(self) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={})
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})
        mock_backend.resolve_skill_config = AsyncMock(return_value={})
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})
        mock_backend.resolve_subagents = AsyncMock(
            side_effect=RuntimeError("Subagent error")
        )

        with patch("app.services.config_resolver.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.default_model = None
            mock_settings.return_value = mock_settings_obj

            resolver = ConfigResolver(backend_client=mock_backend)
            resolver.settings = mock_settings_obj

            result = await resolver.resolve(
                user_id="user-123",
                config_snapshot={},
            )

            # When subagent resolution fails, the key is not set
            assert "subagent_raw_agents" not in result


@pytest.mark.asyncio
class TestConfigResolverGetEnvMap:
    """Test ConfigResolver._get_env_map."""

    async def test_get_env_map(self) -> None:
        mock_backend = MagicMock()
        mock_backend.get_env_map = AsyncMock(return_value={"KEY": "value"})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._get_env_map("user-123")

            assert result == {"KEY": "value"}
            mock_backend.get_env_map.assert_called_once_with(user_id="user-123")


@pytest.mark.asyncio
class TestConfigResolverResolveEffectiveMcpConfig:
    """Test ConfigResolver._resolve_effective_mcp_config."""

    async def test_with_server_ids(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_mcp_config = AsyncMock(return_value={"server1": {}})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_mcp_config(
                "user-123", {"mcp_server_ids": [1, 2]}
            )

            assert "server1" in result
            mock_backend.resolve_mcp_config.assert_called_once()

    async def test_with_explicit_empty_server_ids_disables_all(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_mcp_config = AsyncMock(return_value={})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_mcp_config(
                "user-123",
                {
                    "mcp_server_ids": [],
                    "mcp_config": {"legacy-server": {"command": "uvx"}},
                },
            )

            assert result == {}
            mock_backend.resolve_mcp_config.assert_called_once_with(
                user_id="user-123", server_ids=[]
            )

    async def test_with_toggles(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_mcp_config = AsyncMock(return_value={"server1": {}})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            await resolver._resolve_effective_mcp_config(
                "user-123", {"mcp_config": {"1": True, "2": False}}
            )

            mock_backend.resolve_mcp_config.assert_called_once()

    async def test_with_legacy_config(self) -> None:
        mock_backend = MagicMock()

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_mcp_config(
                "user-123", {"mcp_config": {"server1": {"command": "uvx"}}}
            )

            assert result == {"server1": {"command": "uvx"}}


@pytest.mark.asyncio
class TestConfigResolverResolveEffectiveSkillFiles:
    """Test ConfigResolver._resolve_effective_skill_files."""

    async def test_with_skill_ids(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_skill_config = AsyncMock(return_value={"skill1": {}})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_skill_files(
                "user-123", {"skill_ids": [1]}
            )

            assert "skill1" in result

    async def test_with_legacy_config(self) -> None:
        mock_backend = MagicMock()

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_skill_files(
                "user-123", {"skill_files": {"skill1": {"content": "test"}}}
            )

            assert result == {"skill1": {"content": "test"}}


@pytest.mark.asyncio
class TestConfigResolverResolveEffectivePluginFiles:
    """Test ConfigResolver._resolve_effective_plugin_files."""

    async def test_with_plugin_ids(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_plugin_config = AsyncMock(return_value={"plugin1": {}})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_plugin_files(
                "user-123", {"plugin_ids": [1]}
            )

            assert "plugin1" in result

    async def test_with_explicit_empty_plugin_ids_disables_all(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_plugin_config = AsyncMock(return_value={})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_plugin_files(
                "user-123",
                {
                    "plugin_ids": [],
                    "plugin_files": {"legacy-plugin": {"config": "test"}},
                },
            )

            assert result == {}
            mock_backend.resolve_plugin_config.assert_called_once_with(
                user_id="user-123", plugin_ids=[]
            )

    async def test_with_legacy_config(self) -> None:
        mock_backend = MagicMock()

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_plugin_files(
                "user-123", {"plugin_files": {"plugin1": {"config": "test"}}}
            )

            assert result == {"plugin1": {"config": "test"}}


@pytest.mark.asyncio
class TestConfigResolverResolveEffectiveSubagents:
    """Test ConfigResolver._resolve_effective_subagents."""

    async def test_with_subagent_ids(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_subagents = AsyncMock(
            return_value={"structured_agents": {}, "raw_agents": {}}
        )

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            result = await resolver._resolve_effective_subagents(
                "user-123", {"subagent_ids": [1, 2]}
            )

            assert "structured_agents" in result

    async def test_without_subagent_ids_key(self) -> None:
        mock_backend = MagicMock()
        mock_backend.resolve_subagents = AsyncMock(return_value={})

        resolver = ConfigResolver(backend_client=mock_backend)
        with patch("app.services.config_resolver.get_settings"):
            resolver.settings = MagicMock()

            await resolver._resolve_effective_subagents("user-123", {})

            mock_backend.resolve_subagents.assert_called_once_with(
                user_id="user-123", subagent_ids=None
            )


class TestConfigResolverGetFirstSettingsValue(unittest.TestCase):
    """Test ConfigResolver._get_first_settings_value."""

    def test_found_value(self) -> None:
        mock_settings = MagicMock()
        mock_settings.field1 = None
        mock_settings.field2 = "value2"

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._get_first_settings_value(("field1", "field2"))
        assert result == "value2"

    def test_not_found(self) -> None:
        mock_settings = MagicMock()
        mock_settings.field1 = None
        mock_settings.field2 = None

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._get_first_settings_value(("field1", "field2"))
        assert result == ""


class TestConfigResolverResolveModelEnvOverrides(unittest.TestCase):
    """Test ConfigResolver._resolve_model_env_overrides."""

    def test_no_model(self) -> None:
        mock_settings = MagicMock()
        mock_settings.default_model = None

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._resolve_model_env_overrides({}, {}, user_id="user-123")
        assert result == {}

    def test_anthropic_model(self) -> None:
        mock_settings = MagicMock()
        mock_settings.default_model = None
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_base_url = None

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._resolve_model_env_overrides(
            {"model": "claude-3-opus"},
            {"ANTHROPIC_API_KEY": "env-key"},
            user_id="user-123",
        )

        assert "ANTHROPIC_API_KEY" in result

    def test_missing_api_key(self) -> None:
        mock_settings = MagicMock()
        mock_settings.default_model = None
        mock_settings.anthropic_api_key = None
        mock_settings.glm_api_key = None

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        with pytest.raises(AppException) as exc_info:
            resolver._resolve_model_env_overrides(
                {"model": "claude-3-opus"},
                {},
                user_id="user-123",
            )

        assert exc_info.value.error_code == ErrorCode.ENV_VAR_NOT_FOUND

    def test_explicit_provider_id(self) -> None:
        mock_settings = MagicMock()
        mock_settings.default_model = None
        mock_settings.glm_api_key = "glm-key"

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._resolve_model_env_overrides(
            {"model": "custom-model", "model_provider_id": "glm"},
            {},
            user_id="user-123",
        )

        assert "ANTHROPIC_API_KEY" in result

    def test_explicit_provider_id_does_not_fallback_to_inferred(self) -> None:
        """Explicit providers should never be replaced by inferred runtime defaults."""
        mock_settings = MagicMock()
        mock_settings.default_model = None
        mock_settings.anthropic_api_key = "anthropic-key"

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._resolve_model_env_overrides(
            {"model": "claude-3-opus", "model_provider_id": "unknown-provider"},
            {},
            user_id="user-123",
        )

        assert result == {}

    def test_explicit_provider_not_in_specs_no_inferred(self) -> None:
        """Test when explicit provider_id not in specs and no inferred."""
        mock_settings = MagicMock()
        mock_settings.default_model = None

        resolver = ConfigResolver.__new__(ConfigResolver)
        resolver.settings = mock_settings

        result = resolver._resolve_model_env_overrides(
            {"model": "unknown-model", "model_provider_id": "unknown-provider"},
            {},
            user_id="user-123",
        )

        assert result == {}


if __name__ == "__main__":
    unittest.main()
