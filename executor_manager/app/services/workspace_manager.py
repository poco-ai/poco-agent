import json
import logging
import mimetypes
import shutil
import tarfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceMeta:
    session_id: str
    user_id: str
    task_id: str
    created_at: str
    status: Literal["active", "archived", "deleted"]
    container_mode: Literal["ephemeral", "persistent"]
    workspace_path: str
    size_bytes: int = 0

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


class WorkspaceManager:
    settings: Settings
    base_dir: Path
    active_dir: Path
    archive_dir: Path
    temp_dir: Path

    def __init__(self):
        self.settings = get_settings()
        self.base_dir = Path(self.settings.workspace_root)
        self.active_dir = self.base_dir / "active"
        self.archive_dir = self.base_dir / "archive"
        self.temp_dir = self.base_dir / "temp"
        self.ignore_dot_files = self.settings.workspace_ignore_dot_files

        self._init_directories()

        self._ignore_names = {
            ".git",
            ".hg",
            ".svn",
            ".DS_Store",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            ".venv",
            "venv",
            ".next",
            "dist",
            "build",
        }

    def _init_directories(self) -> None:
        """Initialize directory structure."""
        for directory in [self.active_dir, self.archive_dir, self.temp_dir]:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug("workspace_dir_ready", extra={"path": str(directory)})
            except PermissionError as e:
                raise RuntimeError(
                    f"Permission denied creating workspace directory '{directory}'. "
                    f"Ensure WORKSPACE_ROOT ('{self.base_dir}') is writable by the current user. "
                    f"You may need to: chown -R <uid>:<gid> {self.base_dir} or set a different WORKSPACE_ROOT."
                ) from e

    def get_workspace_path(
        self,
        user_id: str,
        session_id: str,
        create: bool = True,
    ) -> Path:
        """Get workspace path."""
        user_dir = self.active_dir / user_id
        session_dir = user_dir / session_id

        if create:
            user_dir.mkdir(parents=True, exist_ok=True)
            session_dir.mkdir(exist_ok=True)

            (session_dir / "workspace").mkdir(exist_ok=True)
            (session_dir / "logs").mkdir(exist_ok=True)

            self._write_meta(session_dir, user_id, session_id)

        return session_dir

    def get_session_workspace_dir(self, user_id: str, session_id: str) -> Path | None:
        """Get the workspace directory for a session without creating it."""
        session_dir = self.get_workspace_path(
            user_id=user_id,
            session_id=session_id,
            create=False,
        )
        workspace_dir = session_dir / "workspace"
        if not workspace_dir.exists():
            return None
        return workspace_dir

    def resolve_user_id(self, session_id: str) -> str | None:
        """Resolve user_id for a session by scanning workspace roots."""
        if not self.active_dir.exists():
            return None
        for user_dir in self.active_dir.iterdir():
            if not user_dir.is_dir():
                continue
            if (user_dir / session_id).exists():
                return user_dir.name
        return None

    def list_workspace_files(
        self,
        user_id: str,
        session_id: str,
        *,
        max_depth: int = 8,
        max_entries: int = 4000,
    ) -> list[dict]:
        """List workspace files as a tree structure."""
        workspace_dir = self.get_session_workspace_dir(
            user_id=user_id, session_id=session_id
        )
        if not workspace_dir:
            return []

        counter = {"count": 0}
        base = workspace_dir.resolve()

        def build_dir(current: Path, prefix: str, depth: int) -> list[dict]:
            if depth > max_depth:
                return []

            nodes: list[dict] = []
            try:
                entries = sorted(
                    current.iterdir(),
                    key=lambda p: (
                        1 if p.is_file() else 0,
                        p.name.lower(),
                    ),
                )
            except Exception:
                return []

            for entry in entries:
                if counter["count"] >= max_entries:
                    break

                if entry.name in self._ignore_names:
                    continue

                if self.ignore_dot_files and entry.name.startswith("."):
                    continue

                if entry.is_symlink():
                    continue

                rel_path = f"{prefix}/{entry.name}" if prefix else f"/{entry.name}"
                counter["count"] += 1

                if entry.is_dir():
                    children = build_dir(entry, rel_path, depth + 1)
                    nodes.append(
                        {
                            "id": rel_path,
                            "name": entry.name,
                            "type": "folder",
                            "path": rel_path,
                            "children": children,
                        }
                    )
                elif entry.is_file():
                    mime_type, _ = mimetypes.guess_type(entry.name)
                    nodes.append(
                        {
                            "id": rel_path,
                            "name": entry.name,
                            "type": "file",
                            "path": rel_path,
                            "mimeType": mime_type,
                        }
                    )

            return nodes

        return build_dir(base, "", 0)

    def resolve_workspace_file(
        self,
        user_id: str,
        session_id: str,
        file_path: str,
    ) -> Path | None:
        """Resolve a file path within a workspace safely."""
        workspace_dir = self.get_session_workspace_dir(
            user_id=user_id, session_id=session_id
        )
        if not workspace_dir:
            return None

        clean = (file_path or "").strip()
        if not clean:
            return None

        clean = clean.lstrip("/")
        candidate = (workspace_dir / clean).resolve()
        base = workspace_dir.resolve()

        try:
            candidate.relative_to(base)
        except Exception:
            return None

        if not candidate.exists() or not candidate.is_file():
            return None

        return candidate

    def _write_meta(
        self,
        session_dir: Path,
        user_id: str,
        session_id: str,
        task_id: str = "",
        container_mode: Literal["ephemeral", "persistent"] = "ephemeral",
    ) -> None:
        """Write metadata file."""
        meta = WorkspaceMeta(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            created_at=datetime.now().isoformat(),
            status="active",
            container_mode=container_mode,
            workspace_path=str(session_dir / "workspace"),
        )

        meta_file = session_dir / "meta.json"
        _ = meta_file.write_text(json.dumps(meta.to_dict(), indent=2), encoding="utf-8")
        logger.debug(
            "workspace_meta_written",
            extra={"session_id": session_id, "meta_file": str(meta_file)},
        )

    def get_meta(self, user_id: str, session_id: str) -> WorkspaceMeta | None:
        """Read metadata file."""
        meta_file = self.active_dir / user_id / session_id / "meta.json"

        if not meta_file.exists():
            return None

        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return WorkspaceMeta(**data)
        except Exception as e:
            logger.error(f"Failed to read meta file {meta_file}: {e}")
            return None

    def update_meta_status(
        self,
        user_id: str,
        session_id: str,
        status: Literal["active", "archived", "deleted"],
    ) -> None:
        """Update metadata status."""
        meta = self.get_meta(user_id, session_id)
        if meta:
            meta.status = status
            meta_file = self.active_dir / user_id / session_id / "meta.json"
            _ = meta_file.write_text(
                json.dumps(meta.to_dict(), indent=2), encoding="utf-8"
            )

    def get_workspace_volume(self, user_id: str, session_id: str) -> str:
        """Get container mount path."""
        workspace_dir = self.get_workspace_path(user_id, session_id, create=True)
        return str(workspace_dir / "workspace")

    def archive_workspace(
        self,
        user_id: str,
        session_id: str,
        keep_days: int = 7,
    ) -> str | None:
        """Archive workspace."""
        session_dir = self.active_dir / user_id / session_id

        if not session_dir.exists():
            logger.warning(f"Workspace not found: {session_dir}")
            return None

        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            archive_user_dir = self.archive_dir / user_id / date_str
            archive_user_dir.mkdir(parents=True, exist_ok=True)

            archive_file = archive_user_dir / f"{session_id}.tar.gz"

            with tarfile.open(archive_file, "w:gz") as tar:
                tar.add(session_dir, arcname=session_id)

            self.update_meta_status(user_id, session_id, "archived")

            shutil.rmtree(session_dir)

            logger.info(f"Archived workspace: {session_dir} -> {archive_file}")
            return str(archive_file)

        except Exception as e:
            logger.error(f"Failed to archive workspace {session_dir}: {e}")
            return None

    def delete_workspace(
        self,
        user_id: str,
        session_id: str,
        force: bool = False,
    ) -> bool:
        """Delete workspace."""
        meta = self.get_meta(user_id, session_id)

        if meta and not force and meta.container_mode == "persistent":
            logger.warning(
                f"Workspace {session_id} is persistent, use force=True to delete"
            )
            return False

        session_dir = self.active_dir / user_id / session_id

        if not session_dir.exists():
            logger.warning(f"Workspace not found: {session_dir}")
            return False

        try:
            shutil.rmtree(session_dir)
            logger.info(f"Deleted workspace: {session_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete workspace {session_dir}: {e}")
            return False

    def cleanup_expired_workspaces(self, max_age_hours: int = 24) -> dict[str, int]:
        """Clean up expired workspaces."""
        now = datetime.now()
        cleaned = 0
        archived = 0
        errors = 0

        for user_dir in self.active_dir.iterdir():
            if not user_dir.is_dir():
                continue

            for session_dir in user_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                meta = self.get_meta(user_dir.name, session_dir.name)

                if not meta:
                    if self.delete_workspace(
                        user_dir.name, session_dir.name, force=True
                    ):
                        cleaned += 1
                    continue

                created_at = datetime.fromisoformat(meta.created_at)
                age = now - created_at

                if meta.status == "active":
                    if age > timedelta(hours=max_age_hours):
                        logger.info(
                            f"Workspace {session_dir.name} expired (age: {age})"
                        )

                        if meta.container_mode == "ephemeral":
                            if self.delete_workspace(
                                user_dir.name, session_dir.name, force=True
                            ):
                                cleaned += 1
                        else:
                            if self.archive_workspace(user_dir.name, session_dir.name):
                                archived += 1

        return {
            "cleaned": cleaned,
            "archived": archived,
            "errors": errors,
        }

    def get_disk_usage(self) -> dict[str, float | int | str]:
        """Get disk usage statistics."""
        total, used, free = shutil.disk_usage(self.base_dir)

        active_size = self._get_dir_size(self.active_dir)
        archive_size = self._get_dir_size(self.archive_dir)
        temp_size = self._get_dir_size(self.temp_dir)

        return {
            "base_dir": str(self.base_dir),
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round((used / total) * 100, 2),
            "active_size_gb": round(active_size / (1024**3), 2),
            "archive_size_gb": round(archive_size / (1024**3), 2),
            "temp_size_gb": round(temp_size / (1024**3), 2),
            "active_workspaces": sum(1 for _ in self.active_dir.rglob("meta.json")),
            "archived_workspaces": sum(1 for _ in self.archive_dir.rglob("*.tar.gz")),
        }

    def _get_dir_size(self, path: Path) -> int:
        """Get directory size."""
        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total

    def get_user_workspaces(self, user_id: str) -> list[dict[str, str | int]]:
        """Get all workspaces for a user."""
        user_dir = self.active_dir / user_id

        if not user_dir.exists():
            return []

        workspaces: list[dict[str, str | int]] = []
        for session_dir in user_dir.iterdir():
            if not session_dir.is_dir():
                continue

            meta = self.get_meta(user_id, session_dir.name)
            if meta:
                workspaces.append(meta.to_dict())

        return workspaces
