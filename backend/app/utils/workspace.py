from collections.abc import Callable
from typing import Any, Literal

from app.schemas.workspace import FileNode


def build_workspace_file_nodes(
    nodes: list[dict[str, Any]],
    *,
    file_url_builder: Callable[[str], str | None] | None = None,
) -> list[FileNode]:
    """Normalize raw workspace file nodes and optionally attach preview URLs.

    Args:
        nodes: Raw nodes (typically from Executor Manager).
        file_url_builder: Optional callback that returns a URL for a given file path.

    Returns:
        A list of FileNode objects for UI browsing.
    """
    result: list[FileNode] = []

    for node in nodes:
        raw_node_type = node.get("type")
        if raw_node_type not in ("file", "folder"):
            continue
        node_type: Literal["file", "folder"] = raw_node_type
        node_path = node.get("path")
        node_id = node.get("id") or node_path or ""
        name = node.get("name") or ""
        mime_type = node.get("mimeType") or node.get("mime_type")
        oss_status = node.get("oss_status") or node.get("ossStatus")
        oss_meta = node.get("oss_meta") or node.get("ossMeta")
        source = node.get("source") or "workspace"
        mount_id = node.get("mount_id") or node.get("mountId")
        access_mode = node.get("access_mode") or node.get("accessMode")

        children_raw = node.get("children")
        children = (
            build_workspace_file_nodes(
                children_raw,
                file_url_builder=file_url_builder,
            )
            if isinstance(children_raw, list)
            else None
        )

        url = None
        if (
            file_url_builder is not None
            and node_type == "file"
            and isinstance(node_path, str)
            and node_path
        ):
            url = file_url_builder(node_path)

        result.append(
            FileNode(
                id=str(node_id),
                name=str(name),
                type=node_type,
                path=str(node_path or ""),
                children=children,
                url=url,
                mimeType=mime_type,
                oss_status=oss_status,
                oss_meta=oss_meta,
                source=str(source),
                mount_id=str(mount_id) if mount_id is not None else None,
                access_mode=str(access_mode) if access_mode is not None else None,
            )
        )

    return result
