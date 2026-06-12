from typing import Any

from app.schemas.workspace import FileNode
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_manifest,
    extract_manifest_files,
    normalize_manifest_path,
)


def build_workspace_file_nodes_from_export(
    *,
    manifest_key: str | None,
    workspace_files_prefix: str | None,
    storage_service: Any,
) -> list[FileNode]:
    """Build readonly workspace file nodes from an exported workspace manifest."""
    if not manifest_key:
        return []

    manifest = storage_service.get_manifest(manifest_key)
    raw_nodes = build_nodes_from_manifest(manifest)
    manifest_files = extract_manifest_files(manifest)
    prefix = (workspace_files_prefix or "").rstrip("/")
    file_url_map: dict[str, str] = {}

    for file_entry in manifest_files:
        file_path = normalize_manifest_path(file_entry.get("path"))
        if not file_path:
            continue
        object_key = (
            file_entry.get("key")
            or file_entry.get("object_key")
            or file_entry.get("oss_key")
            or file_entry.get("s3_key")
        )
        if not object_key and prefix:
            object_key = f"{prefix}/{file_path.lstrip('/')}"
        if not object_key:
            continue
        mime_type = file_entry.get("mimeType") or file_entry.get("mime_type")
        file_url_map[file_path] = storage_service.presign_get(
            object_key,
            response_content_disposition="inline",
            response_content_type=mime_type,
        )

    def build_file_url(file_path: str) -> str | None:
        normalized = normalize_manifest_path(file_path) or file_path
        return file_url_map.get(normalized)

    return build_workspace_file_nodes(raw_nodes, file_url_builder=build_file_url)
