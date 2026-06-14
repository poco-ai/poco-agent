from collections.abc import Callable
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.settings import get_settings
from app.schemas.workspace import FileNode
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_manifest,
    extract_manifest_files,
    normalize_manifest_path,
)

WORKSPACE_PREVIEW_TOKEN_MAX_AGE_SECONDS = 300
_WORKSPACE_PREVIEW_TOKEN_SALT = "workspace-preview"


def build_workspace_file_nodes_from_export(
    *,
    manifest_key: str | None,
    workspace_files_prefix: str | None,
    storage_service: Any,
    file_url_builder: Callable[[str], str | None] | None = None,
) -> list[FileNode]:
    """Build readonly workspace file nodes from an exported workspace manifest."""
    if not manifest_key:
        return []

    manifest = storage_service.get_manifest(manifest_key)
    raw_nodes = build_nodes_from_manifest(manifest)
    manifest_files = extract_manifest_files(manifest)
    file_url_map: dict[str, str] = {}

    for file_entry in manifest_files:
        file_path = normalize_manifest_path(file_entry.get("path"))
        if not file_path:
            continue
        object_key = resolve_export_object_key(
            file_entry=file_entry,
            workspace_files_prefix=workspace_files_prefix,
        )
        if not object_key:
            continue
        mime_type = file_entry.get("mimeType") or file_entry.get("mime_type")
        if file_url_builder is not None:
            url = file_url_builder(file_path)
        else:
            url = storage_service.presign_get(
                object_key,
                response_content_disposition="inline",
                response_content_type=mime_type,
            )
        if url:
            file_url_map[file_path] = url

    def build_file_url(file_path: str) -> str | None:
        normalized = normalize_manifest_path(file_path) or file_path
        return file_url_map.get(normalized)

    return build_workspace_file_nodes(raw_nodes, file_url_builder=build_file_url)


def resolve_export_object_key(
    *,
    file_entry: dict[str, Any],
    workspace_files_prefix: str | None,
) -> str | None:
    """Resolve the object storage key for a file entry in a workspace export."""
    object_key = (
        file_entry.get("key")
        or file_entry.get("object_key")
        or file_entry.get("oss_key")
        or file_entry.get("s3_key")
    )
    if isinstance(object_key, str) and object_key.strip():
        return object_key

    prefix = (workspace_files_prefix or "").rstrip("/")
    file_path = normalize_manifest_path(file_entry.get("path"))
    if prefix and file_path:
        return f"{prefix}/{file_path.lstrip('/')}"
    return None


def create_workspace_preview_token(*, scope: str, scope_id: str) -> str:
    serializer = URLSafeTimedSerializer(
        get_settings().secret_key,
        salt=_WORKSPACE_PREVIEW_TOKEN_SALT,
    )
    return serializer.dumps({"scope": scope, "scope_id": scope_id})


def verify_workspace_preview_token(
    token: str | None,
    *,
    scope: str,
    scope_id: str,
) -> bool:
    if not token:
        return False
    serializer = URLSafeTimedSerializer(
        get_settings().secret_key,
        salt=_WORKSPACE_PREVIEW_TOKEN_SALT,
    )
    try:
        payload = serializer.loads(
            token,
            max_age=WORKSPACE_PREVIEW_TOKEN_MAX_AGE_SECONDS,
        )
    except (BadSignature, SignatureExpired):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("scope") == scope
        and payload.get("scope_id") == scope_id
    )
