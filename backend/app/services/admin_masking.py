from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEYWORDS = (
    "secret",
    "token",
    "password",
    "passwd",
    "auth",
    "bearer",
    "credential",
    "credentials",
    "api_key",
    "apikey",
    "api-token",
    "x-api-key",
    "access_key",
    "access_token",
    "refresh_token",
    "id_token",
    "private_key",
    "secret_key",
    "app_secret",
    "app_key",
    "client_key",
    "client_secret",
    "authorization",
    "sign",
    "signature",
    "signing_key",
    "webhook_secret",
    "session_key",
    "session_token",
    "license_key",
    "connection_string",
    "database_url",
    "dsn",
    "pat",
)


def _looks_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    lowered = normalized.lower()
    return any(keyword in lowered for keyword in SENSITIVE_KEYWORDS)


def _normalize_key(key: str) -> str:
    trimmed = key.strip()
    if not trimmed:
        return ""

    snake_like = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", trimmed)
    snake_like = re.sub(r"[^a-zA-Z0-9]+", "_", snake_like)
    snake_like = re.sub(r"_+", "_", snake_like)
    return snake_like.strip("_").lower()


def _mask_string(value: str) -> str:
    clean = value.strip()
    if not clean:
        return value
    if len(clean) <= 8:
        return "*" * len(clean)
    return f"{clean[:4]}...{clean[-4:]}"


def mask_sensitive_structure(
    value: Any, parent_key: str | None = None
) -> tuple[Any, bool]:
    if isinstance(value, Mapping):
        masked: dict[str, Any] = {}
        contains_sensitive = False
        for key, item in value.items():
            child_parent = str(key)
            child_masked, child_sensitive = mask_sensitive_structure(item, child_parent)
            masked[str(key)] = child_masked
            contains_sensitive = contains_sensitive or child_sensitive
        return masked, contains_sensitive

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        masked_items: list[Any] = []
        contains_sensitive = False
        for item in value:
            child_masked, child_sensitive = mask_sensitive_structure(item, parent_key)
            masked_items.append(child_masked)
            contains_sensitive = contains_sensitive or child_sensitive
        return masked_items, contains_sensitive

    if isinstance(value, str) and parent_key and _looks_sensitive_key(parent_key):
        return _mask_string(value), True

    return value, False
