#!/usr/bin/env python3
"""Submit a generated skill folder for review."""

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath


_VISIBLE_SKILL_ROOT = PurePosixPath("/.config/skills")
_VISIBLE_DRAFT_ROOT = PurePosixPath("/skills")


def _get_env_value(*keys: str) -> str:
    for key in keys:
        value = str(os.environ.get(key, "")).strip()
        if value:
            return value
    return ""


def _candidate_context_paths() -> list[Path]:
    candidates: list[Path] = []

    explicit_path = _get_env_value("POCO_TASK_CONTEXT_PATH")
    if explicit_path:
        candidates.append(Path(explicit_path))

    workspace_path = _get_env_value("WORKSPACE_PATH")
    if workspace_path:
        candidates.append(Path(workspace_path) / ".poco-task-context.json")

    cwd = Path.cwd().resolve()
    candidates.extend(parent / ".poco-task-context.json" for parent in (cwd, *cwd.parents))

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _load_task_context_from_file() -> dict[str, str]:
    context_path = next((path for path in _candidate_context_paths() if path.exists()), None)
    if context_path is None:
        attempted = ", ".join(str(path) for path in _candidate_context_paths())
        raise RuntimeError(f"Task context file not found. Checked: {attempted}")

    payload = json.loads(context_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Task context file is invalid")

    session_id = str(payload.get("session_id", "")).strip()
    callback_base_url = str(payload.get("callback_base_url", "")).strip()
    callback_token = str(payload.get("callback_token", "")).strip()
    if not session_id or not callback_base_url or not callback_token:
        raise RuntimeError("Task context is missing required fields")

    return {
        "session_id": session_id,
        "callback_base_url": callback_base_url.rstrip("/"),
        "callback_token": callback_token,
    }


def _load_task_context() -> dict[str, str]:
    session_id = _get_env_value("POCO_SESSION_ID", "SESSION_ID")
    callback_base_url = _get_env_value(
        "POCO_CALLBACK_BASE_URL",
        "CALLBACK_BASE_URL",
    )
    callback_token = _get_env_value(
        "POCO_CALLBACK_TOKEN",
        "CALLBACK_TOKEN",
    )

    if session_id and callback_base_url and callback_token:
        return {
            "session_id": session_id,
            "callback_base_url": callback_base_url.rstrip("/"),
            "callback_token": callback_token,
        }

    return _load_task_context_from_file()


def _normalize_workspace_path(path: str) -> str:
    normalized = (path or "").replace("\\", "/").strip()
    if not normalized:
        raise RuntimeError("Skill folder path is required")
    if normalized == "/workspace":
        raise RuntimeError("Skill folder path must point to a folder, not /workspace")
    if normalized.startswith("/workspace/"):
        normalized = normalized[len("/workspace/") :]
    normalized = "/" + normalized.lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise RuntimeError(f"Invalid workspace folder path: {path}")
    return "/" + "/".join(parts)


def _candidate_workspace_roots() -> list[Path]:
    roots: list[Path] = []
    workspace_path = _get_env_value("WORKSPACE_PATH")
    if workspace_path:
        roots.append(Path(workspace_path))

    for context_path in _candidate_context_paths():
        roots.append(context_path.parent)

    cwd = Path.cwd().resolve()
    roots.extend((cwd, *cwd.parents))

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in roots:
        resolved = candidate.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolved)
    return deduped


def _find_workspace_root() -> Path:
    for candidate in _candidate_workspace_roots():
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise RuntimeError("Workspace root not found")


def _resolve_workspace_dir(workspace_root: Path, relative_path: str) -> Path:
    candidate = (workspace_root / relative_path.lstrip("/")).resolve()
    base = workspace_root.resolve()
    try:
        candidate.relative_to(base)
    except Exception as exc:
        raise RuntimeError("Skill folder path escapes workspace") from exc
    return candidate


def _is_under(path: str, root: PurePosixPath) -> bool:
    return PurePosixPath(path).is_relative_to(root)


def _prefer_visible_workspace_draft(
    *,
    workspace_root: Path,
    normalized_folder_path: str,
    source_dir: Path,
) -> tuple[str, Path]:
    if not _is_under(normalized_folder_path, _VISIBLE_SKILL_ROOT):
        return normalized_folder_path, source_dir

    skill_name = source_dir.name
    visible_draft_path = (_VISIBLE_DRAFT_ROOT / skill_name).as_posix()
    visible_draft_dir = _resolve_workspace_dir(workspace_root, visible_draft_path)
    if not visible_draft_dir.is_dir():
        return normalized_folder_path, source_dir
    if not (visible_draft_dir / "SKILL.md").is_file():
        return normalized_folder_path, source_dir

    print(
        "Using visible workspace draft "
        f"{visible_draft_path.lstrip('/')} instead of {normalized_folder_path.lstrip('/')}.",
        file=sys.stderr,
    )
    return visible_draft_path, visible_draft_dir


def _copy_to_visible_skill_root(
    *,
    workspace_root: Path,
    source_dir: Path,
    source_label: str,
) -> str:
    destination_path = (_VISIBLE_SKILL_ROOT / source_dir.name).as_posix()
    destination_dir = _resolve_workspace_dir(workspace_root, destination_path)
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    if source_dir.resolve() != destination_dir.resolve():
        if destination_dir.exists():
            shutil.rmtree(destination_dir)
        shutil.copytree(source_dir, destination_dir)
    print(
        "Prepared review copy at "
        f"{destination_path.lstrip('/')} from {source_label}.",
        file=sys.stderr,
    )
    return destination_path


def _prepare_submission_folder(folder_path: str) -> str:
    workspace_root = _find_workspace_root()
    raw_folder = (folder_path or "").strip()
    source_label = raw_folder or folder_path

    if raw_folder == "/workspace" or raw_folder.startswith("/workspace/"):
        normalized_folder_path = _normalize_workspace_path(raw_folder)
        source_dir = _resolve_workspace_dir(workspace_root, normalized_folder_path)
    elif Path(raw_folder).is_absolute():
        source_dir = Path(raw_folder).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise RuntimeError(f"Skill folder not found: {raw_folder}")
        if not (source_dir / "SKILL.md").is_file():
            raise RuntimeError(f"Skill folder is missing SKILL.md: {raw_folder}")
        try:
            relative = source_dir.relative_to(workspace_root.resolve())
        except Exception:
            return _copy_to_visible_skill_root(
                workspace_root=workspace_root,
                source_dir=source_dir,
                source_label=f"external folder {raw_folder}",
            )
        normalized_folder_path = "/" + relative.as_posix().lstrip("/")
    else:
        normalized_folder_path = _normalize_workspace_path(raw_folder)
        source_dir = _resolve_workspace_dir(workspace_root, normalized_folder_path)

    if not source_dir.exists() or not source_dir.is_dir():
        raise RuntimeError(f"Skill folder not found: {normalized_folder_path}")
    if not (source_dir / "SKILL.md").is_file():
        raise RuntimeError(f"Skill folder is missing SKILL.md: {normalized_folder_path}")

    normalized_folder_path, source_dir = _prefer_visible_workspace_draft(
        workspace_root=workspace_root,
        normalized_folder_path=normalized_folder_path,
        source_dir=source_dir,
    )

    if _is_under(normalized_folder_path, _VISIBLE_SKILL_ROOT):
        return normalized_folder_path

    return _copy_to_visible_skill_root(
        workspace_root=workspace_root,
        source_dir=source_dir,
        source_label=f"workspace folder {normalized_folder_path}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Submit a workspace skill folder for review",
    )
    parser.add_argument(
        "--folder",
        required=True,
        help=(
            "Skill folder path relative to the workspace, an absolute path under "
            "/workspace, or an external local folder. Non-.config skill folders "
            "are copied into .config/skills/<name> automatically for review. "
            "Recommended authoring path: /workspace/skills/<skill-name>."
        ),
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional skill name override",
    )
    args = parser.parse_args()

    try:
        context = _load_task_context()
        folder_path = _prepare_submission_folder(args.folder)
        request = urllib.request.Request(
            f"{context['callback_base_url']}/api/v1/skills/submit",
            data=json.dumps(
                {
                    "session_id": context["session_id"],
                    "folder_path": folder_path,
                    "skill_name": args.name,
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {context['callback_token']}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Failed to submit skill for review: HTTP {exc.code} {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Failed to submit skill for review: {exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Failed to submit skill for review: {exc}", file=sys.stderr)
        return 1

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    pending_id = data.get("pending_id")
    status = data.get("status")
    if pending_id:
        print(
            "Skill submitted for review successfully. "
            f"pending_id={pending_id} status={status or 'pending'}"
        )
    else:
        print("Skill submitted for review successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
