from __future__ import annotations

from typing import Any

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException


_MCP_ALLOWED_TRANSPORT_TYPES = {"http", "stdio"}
_MCP_RESERVED_SERVER_KEY_PREFIXES = ("__poco_",)


def extract_single_mcp_server_key(raw: Any) -> str | None:
    """Extract the single MCP server key from a Claude-style wrapper config.

    Returns None if the config does not match the expected shape:
    {"mcpServers": {"<key>": {...}}}
    """
    if not isinstance(raw, dict):
        return None
    mcp_servers = raw.get("mcpServers")
    if not isinstance(mcp_servers, dict) or len(mcp_servers) != 1:
        return None
    key = next(iter(mcp_servers.keys()), None)
    if not isinstance(key, str):
        return None
    clean = key.strip()
    return clean or None


def normalize_mcp_server_config(raw: Any, *, default_server_key: str) -> dict[str, Any]:
    """Validate and normalize an MCP server config before persisting.

    Accepted input shapes:
    1) Claude Code wrapper:
       {"mcpServers": {"<serverKey>": { ...serverDef... }}}
    2) Server-only definition:
       { ...serverDef... }

    Normalized output is always in wrapper shape and contains exactly one entry.
    """

    errors: list[dict[str, str]] = []
    if not isinstance(raw, dict):
        errors.append(
            {"path": "server_config", "message": "server_config must be an object"}
        )
        _raise_invalid_mcp_server_config(errors)

    if "mcpServers" in raw:
        mcp_servers = raw.get("mcpServers")
        if not isinstance(mcp_servers, dict):
            errors.append(
                {"path": "mcpServers", "message": "mcpServers must be an object"}
            )
            _raise_invalid_mcp_server_config(errors)
        if len(mcp_servers) != 1:
            errors.append(
                {
                    "path": "mcpServers",
                    "message": "mcpServers must contain exactly one server",
                }
            )
            _raise_invalid_mcp_server_config(errors)

        raw_key, raw_def = next(iter(mcp_servers.items()))
        server_key = _normalize_mcp_server_key(raw_key, errors, path="mcpServers.<key>")
        server_path = f"mcpServers.{server_key or '<server>'}"
        server_def = _normalize_mcp_server_def(raw_def, errors, path=server_path)
        if errors:
            _raise_invalid_mcp_server_config(errors)
        assert server_def is not None

        normalized = dict(raw)
        normalized["mcpServers"] = {server_key: server_def}
        return normalized

    server_key = _normalize_mcp_server_key(
        default_server_key, errors, path="mcpServers.<key>"
    )
    server_path = f"mcpServers.{server_key or '<server>'}"
    server_def = _normalize_mcp_server_def(raw, errors, path=server_path)
    if errors:
        _raise_invalid_mcp_server_config(errors)
    assert server_def is not None
    return {"mcpServers": {server_key: server_def}}


def _raise_invalid_mcp_server_config(errors: list[dict[str, str]]) -> None:
    message = (
        errors[0].get("message")
        if errors and isinstance(errors[0].get("message"), str)
        else ErrorCode.MCP_SERVER_INVALID_CONFIG.message
    )
    raise AppException(
        error_code=ErrorCode.MCP_SERVER_INVALID_CONFIG,
        message=message,
        details={"errors": errors},
    )


def _normalize_mcp_server_key(
    value: Any, errors: list[dict[str, str]], *, path: str
) -> str:
    if not isinstance(value, str):
        errors.append({"path": path, "message": "MCP server key must be a string"})
        return ""
    clean = value.strip()
    if not clean:
        errors.append({"path": path, "message": "MCP server key cannot be empty"})
        return ""
    if clean.startswith(_MCP_RESERVED_SERVER_KEY_PREFIXES):
        errors.append(
            {
                "path": path,
                "message": "MCP server key uses a reserved prefix: __poco_",
            }
        )
        return ""
    return clean


def _normalize_headers(
    value: Any,
    errors: list[dict[str, str]],
    *,
    path: str,
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append({"path": path, "message": "headers must be an object"})
        return None
    normalized: dict[str, str] = {}
    for key, raw_val in value.items():
        if not isinstance(key, str):
            errors.append(
                {"path": f"{path}.*", "message": "header name must be a string"}
            )
            continue
        header_name = key.strip()
        if not header_name:
            errors.append(
                {"path": f"{path}.{key}", "message": "header name cannot be empty"}
            )
            continue
        if not isinstance(raw_val, str):
            errors.append(
                {
                    "path": f"{path}.{header_name}",
                    "message": "header value must be a string",
                }
            )
            continue
        normalized[header_name] = raw_val
    return normalized


def _normalize_env_map(
    value: Any,
    errors: list[dict[str, str]],
    *,
    path: str,
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append({"path": path, "message": "env must be an object"})
        return None
    normalized: dict[str, str] = {}
    for key, raw_val in value.items():
        if not isinstance(key, str):
            errors.append(
                {"path": f"{path}.*", "message": "env var name must be a string"}
            )
            continue
        env_key = key.strip()
        if not env_key:
            errors.append(
                {"path": f"{path}.{key}", "message": "env var name cannot be empty"}
            )
            continue
        if not isinstance(raw_val, str):
            errors.append(
                {
                    "path": f"{path}.{env_key}",
                    "message": "env var value must be a string",
                }
            )
            continue
        normalized[env_key] = raw_val
    return normalized


def _require_http_url(
    value: Any, errors: list[dict[str, str]], *, path: str
) -> str | None:
    if not isinstance(value, str):
        errors.append({"path": path, "message": "url must be a string"})
        return None
    url = value.strip()
    if not url:
        errors.append({"path": path, "message": "url cannot be empty"})
        return None
    if "://" not in url:
        errors.append(
            {"path": path, "message": "url must start with http:// or https://"}
        )
        return None
    scheme = url.split("://", 1)[0].strip().lower()
    if scheme not in {"http", "https"}:
        errors.append(
            {"path": path, "message": "url must start with http:// or https://"}
        )
        return None
    return url


def _normalize_mcp_server_def(
    raw: Any,
    errors: list[dict[str, str]],
    *,
    path: str,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        errors.append({"path": path, "message": "MCP server config must be an object"})
        return None

    inferred_type: str | None = None
    type_raw = raw.get("type")
    if isinstance(type_raw, str) and type_raw.strip():
        inferred_type = type_raw.strip().lower()
    else:
        if "command" in raw:
            inferred_type = "stdio"
        elif "url" in raw:
            inferred_type = "http"

    if not inferred_type:
        errors.append(
            {
                "path": f"{path}.type",
                "message": "type is required (supported: http, stdio)",
            }
        )
        return None

    if inferred_type == "sse":
        errors.append(
            {
                "path": f"{path}.type",
                "message": "SSE transport is deprecated and is no longer supported",
            }
        )
        return None

    if inferred_type not in _MCP_ALLOWED_TRANSPORT_TYPES:
        errors.append(
            {
                "path": f"{path}.type",
                "message": f"Unsupported MCP transport type: {inferred_type}",
            }
        )
        return None

    normalized: dict[str, Any] = dict(raw)
    normalized["type"] = inferred_type

    if inferred_type == "http":
        url = _require_http_url(raw.get("url"), errors, path=f"{path}.url")
        if url is not None:
            normalized["url"] = url
        headers = _normalize_headers(raw.get("headers"), errors, path=f"{path}.headers")
        if headers is not None:
            normalized["headers"] = headers

    if inferred_type == "stdio":
        command_raw = raw.get("command")
        if not isinstance(command_raw, str):
            errors.append(
                {"path": f"{path}.command", "message": "command must be a string"}
            )
        else:
            command = command_raw.strip()
            if not command:
                errors.append(
                    {"path": f"{path}.command", "message": "command cannot be empty"}
                )
            else:
                normalized["command"] = command

        args_raw = raw.get("args")
        if args_raw is not None:
            if not isinstance(args_raw, list):
                errors.append(
                    {
                        "path": f"{path}.args",
                        "message": "args must be a list of strings",
                    }
                )
            else:
                args: list[str] = []
                for i, item in enumerate(args_raw):
                    if not isinstance(item, str):
                        errors.append(
                            {
                                "path": f"{path}.args[{i}]",
                                "message": "args must be a list of strings",
                            }
                        )
                        continue
                    args.append(item)
                normalized["args"] = args

        env = _normalize_env_map(raw.get("env"), errors, path=f"{path}.env")
        if env is not None:
            normalized["env"] = env

    return normalized
