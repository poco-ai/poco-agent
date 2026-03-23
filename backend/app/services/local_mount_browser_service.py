import mimetypes
import shutil
import tempfile
from pathlib import Path

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.schemas.filesystem import LocalMountConfig
from app.schemas.session import TaskConfig
from app.schemas.workspace import FileNode

_LOCAL_MOUNT_PREFIX = "local-mounts"
_FORBIDDEN_ROOTS = {
    "/",
    "/bin",
    "/dev",
    "/etc",
    "/Library",
    "/private",
    "/proc",
    "/sbin",
    "/sys",
    "/System",
    "/tmp",
    "/usr",
    "/var",
}


class LocalMountBrowserService:
    """Browse and safely resolve session-authorized local mount files."""

    def get_session_mount_config(self, session: AgentSession) -> TaskConfig:
        """Return the effective session config for local mount browsing."""
        return self._get_session_mount_config(session)

    def list_files(
        self,
        session: AgentSession,
        *,
        max_depth: int = 8,
        max_entries: int = 4000,
    ) -> list[FileNode]:
        mounts = self._get_session_mounts(session)
        counter = {"count": 0}
        result: list[FileNode] = []

        for mount in mounts:
            root_path = self._normalize_mount_root(mount.host_path)
            root_node = FileNode(
                id=f"{_LOCAL_MOUNT_PREFIX}/{mount.id}",
                name=mount.name,
                type="folder",
                path=f"{_LOCAL_MOUNT_PREFIX}/{mount.id}",
                source="local_mount",
                mount_id=mount.id,
                access_mode=mount.access_mode,
                children=self._build_dir_nodes(
                    root_path=root_path,
                    current=root_path,
                    mount_id=mount.id,
                    access_mode=mount.access_mode,
                    max_depth=max_depth,
                    max_entries=max_entries,
                    counter=counter,
                    depth=0,
                ),
            )
            result.append(root_node)

        return result

    def resolve_file(
        self,
        session: AgentSession,
        *,
        mount_id: str,
        path: str,
    ) -> tuple[Path, TaskConfig]:
        target, config, _ = self._resolve_path(
            session,
            mount_id=mount_id,
            path=path,
            expect_directory=False,
        )
        if not target.is_file():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Local mount file not found",
            )
        return target, config

    def resolve_directory(
        self,
        session: AgentSession,
        *,
        mount_id: str,
        path: str,
    ) -> tuple[Path, TaskConfig]:
        target, config, _ = self._resolve_path(
            session,
            mount_id=mount_id,
            path=path,
            expect_directory=True,
        )
        if not target.is_dir():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Local mount folder not found",
            )
        return target, config

    def create_folder_archive(
        self,
        session: AgentSession,
        *,
        mount_id: str,
        path: str,
    ) -> tuple[Path, str]:
        target, config = self.resolve_directory(
            session,
            mount_id=mount_id,
            path=path,
        )
        folder_name = self.build_archive_filename(
            config=config,
            mount_id=mount_id,
            path=path,
        ).removesuffix(".zip")
        temp_root = Path(tempfile.mkdtemp(prefix="poco-local-mount-archive-"))
        archive_base = temp_root / "archive"
        archive_path = Path(
            shutil.make_archive(
                str(archive_base),
                "zip",
                root_dir=target.parent,
                base_dir=target.name,
            )
        )
        return archive_path, f"{folder_name}.zip"

    def build_archive_filename(
        self,
        *,
        config: TaskConfig,
        mount_id: str,
        path: str,
    ) -> str:
        mount = self._local_mounts_by_id(config).get(mount_id)
        if mount is None:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message=f"Local mount is not authorized for this session: {mount_id}",
            )
        folder_name = (
            self._extract_relative_path(mount_id, path).strip("/").split("/")[-1]
            or mount.name
        )
        return f"{folder_name}.zip"

    def _resolve_path(
        self,
        session: AgentSession,
        *,
        mount_id: str,
        path: str,
        expect_directory: bool,
    ) -> tuple[Path, TaskConfig, LocalMountConfig]:
        config = self.get_session_mount_config(session)
        mount = self._local_mounts_by_id(config).get(mount_id)
        if mount is None:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message=f"Local mount is not authorized for this session: {mount_id}",
            )

        root_path = self._normalize_mount_root(mount.host_path)
        relative_path = self._extract_relative_path(mount_id, path)
        candidate = (
            (root_path / relative_path).resolve(strict=False)
            if relative_path
            else root_path
        )
        try:
            candidate.relative_to(root_path)
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Path escapes the authorized local mount",
            ) from exc

        if not candidate.exists():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Local mount path not found",
            )
        if expect_directory and not candidate.is_dir():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Expected a local mount directory",
            )
        if not expect_directory and not candidate.is_file():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Expected a local mount file",
            )
        return candidate, config, mount

    @staticmethod
    def _build_dir_nodes(
        *,
        root_path: Path,
        current: Path,
        mount_id: str,
        access_mode: str,
        max_depth: int,
        max_entries: int,
        counter: dict[str, int],
        depth: int,
    ) -> list[FileNode]:
        if depth > max_depth:
            return []

        try:
            entries = sorted(
                current.iterdir(),
                key=lambda item: (1 if item.is_file() else 0, item.name.lower()),
            )
        except Exception:
            return []

        nodes: list[FileNode] = []
        for entry in entries:
            if counter["count"] >= max_entries:
                break
            if entry.is_symlink():
                continue

            try:
                relative = entry.resolve(strict=False).relative_to(root_path)
            except Exception:
                continue

            relative_path = relative.as_posix()
            node_path = f"{_LOCAL_MOUNT_PREFIX}/{mount_id}/{relative_path}"
            counter["count"] += 1

            if entry.is_dir():
                nodes.append(
                    FileNode(
                        id=node_path,
                        name=entry.name,
                        type="folder",
                        path=node_path,
                        source="local_mount",
                        mount_id=mount_id,
                        access_mode=access_mode,
                        children=LocalMountBrowserService._build_dir_nodes(
                            root_path=root_path,
                            current=entry,
                            mount_id=mount_id,
                            access_mode=access_mode,
                            max_depth=max_depth,
                            max_entries=max_entries,
                            counter=counter,
                            depth=depth + 1,
                        ),
                    )
                )
                continue

            mime_type, _ = mimetypes.guess_type(entry.name)
            nodes.append(
                FileNode(
                    id=node_path,
                    name=entry.name,
                    type="file",
                    path=node_path,
                    source="local_mount",
                    mount_id=mount_id,
                    access_mode=access_mode,
                    mimeType=mime_type,
                )
            )

        return nodes

    @staticmethod
    def _get_session_mounts(session: AgentSession) -> list:
        config = LocalMountBrowserService._get_session_mount_config(session)
        return config.local_mounts

    @staticmethod
    def _get_session_mount_config(session: AgentSession) -> TaskConfig:
        config = TaskConfig.model_validate(session.config_snapshot or {})
        if config.filesystem_mode != "local_mount":
            return TaskConfig(
                filesystem_mode="sandbox",
                local_mounts=[],
            )
        return config

    @staticmethod
    def _normalize_mount_root(host_path: str) -> Path:
        root = Path(host_path).resolve(strict=False)
        root_text = str(root)
        if not root.is_absolute():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Local mount path must be absolute",
            )
        if root_text in _FORBIDDEN_ROOTS:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Refusing to browse restricted directory: {root_text}",
            )
        if not root.exists() or not root.is_dir():
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Local mount directory is unavailable: {root_text}",
            )
        return root

    @staticmethod
    def _extract_relative_path(mount_id: str, path: str) -> str:
        normalized = (path or "").strip().lstrip("/")
        prefix = f"{_LOCAL_MOUNT_PREFIX}/{mount_id}".strip("/")
        if normalized == prefix:
            return ""
        if normalized.startswith(f"{prefix}/"):
            return normalized[len(prefix) + 1 :]
        return normalized

    @staticmethod
    def _local_mounts_by_id(config: TaskConfig) -> dict[str, LocalMountConfig]:
        return {mount.id: mount for mount in config.local_mounts}
