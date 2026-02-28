from typing import Any, cast


def normalize_manifest_path(path: str | None) -> str | None:
    if not path or not isinstance(path, str):
        return None
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        return None
    normalized = "/" + normalized.lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if any(part in ("..", ".") for part in parts):
        return None
    return "/" + "/".join(parts)


def _flatten_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []

    def visit(items: list[dict[str, Any]]) -> None:
        for node in items:
            if not isinstance(node, dict):
                continue
            node_type = node.get("type")
            if node_type == "file":
                files.append(node)
            elif node_type == "folder":
                children = node.get("children")
                if isinstance(children, list):
                    visit(children)

    visit(nodes)
    return files


def extract_manifest_files(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        files = manifest.get("files")
        if isinstance(files, list):
            return [f for f in files if isinstance(f, dict)]
        nodes = manifest.get("nodes")
        if isinstance(nodes, list):
            return _flatten_nodes(nodes)
    if isinstance(manifest, list):
        return [f for f in manifest if isinstance(f, dict)]
    return []


def build_nodes_from_manifest(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        nodes = manifest.get("nodes")
        if isinstance(nodes, list):
            return nodes

    files = extract_manifest_files(manifest)
    return _build_tree_from_files(files)


def _build_tree_from_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tree: dict[str, dict[str, Any]] = {}

    for item in files:
        raw_path = item.get("path")
        normalized = normalize_manifest_path(raw_path)
        if not normalized:
            continue
        parts = [p for p in normalized.strip("/").split("/") if p]
        if not parts:
            continue

        current: dict[str, dict[str, Any]] = tree
        for index, part in enumerate(parts):
            is_last = index == len(parts) - 1
            if is_last:
                current[part] = {
                    "type": "file",
                    "name": part,
                    "path": normalized,
                    "mimeType": item.get("mimeType") or item.get("mime_type"),
                    "oss_status": item.get("status") or item.get("oss_status"),
                    "oss_meta": _build_oss_meta(item),
                }
            else:
                node = current.get(part)
                if not isinstance(node, dict) or node.get("type") != "folder":
                    folder_path = "/" + "/".join(parts[: index + 1])
                    node = {
                        "type": "folder",
                        "name": part,
                        "path": folder_path,
                        "children": {},
                    }
                    current[part] = node
                children = node.get("children")
                if not isinstance(children, dict):
                    children = {}
                    node["children"] = children
                current = cast(dict[str, dict[str, Any]], children)

    return _tree_to_nodes(tree)


def _build_oss_meta(item: dict[str, Any]) -> dict[str, Any] | None:
    meta: dict[str, Any] = {}
    for key in ("key", "etag", "size", "last_modified", "sha256", "md5"):
        if key in item and item[key] is not None:
            meta[key] = item[key]
    return meta or None


def _tree_to_nodes(tree: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, str]:
        name, payload = item
        return (0 if payload.get("type") == "folder" else 1, name.lower())

    for name, payload in sorted(tree.items(), key=sort_key):
        node_type = payload.get("type")
        if node_type == "folder":
            children = _tree_to_nodes(payload.get("children", {}))
            nodes.append(
                {
                    "id": payload.get("path") or name,
                    "name": payload.get("name") or name,
                    "type": "folder",
                    "path": payload.get("path") or f"/{name}",
                    "children": children,
                }
            )
        else:
            nodes.append(
                {
                    "id": payload.get("path") or name,
                    "name": payload.get("name") or name,
                    "type": "file",
                    "path": payload.get("path") or f"/{name}",
                    "mimeType": payload.get("mimeType"),
                    "oss_status": payload.get("oss_status"),
                    "oss_meta": payload.get("oss_meta"),
                }
            )

    return nodes


def find_manifest_file(manifest: Any, path: str) -> dict[str, Any] | None:
    normalized = normalize_manifest_path(path)
    if not normalized:
        return None
    for item in extract_manifest_files(manifest):
        item_path = normalize_manifest_path(item.get("path"))
        if item_path == normalized:
            return item
    return None
