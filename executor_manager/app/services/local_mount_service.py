"""Local mount resolution for executor containers.

When executor-manager creates executor containers through `/var/run/docker.sock`,
Docker resolves bind mount source paths from the host filesystem, not from the
manager container filesystem. Validation here therefore checks only path shape
and forbidden roots; Docker performs the actual existence and type checks when
the executor container is created.
"""

import logging
import re
from pathlib import Path
from typing import Any, Protocol

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import Settings
from app.schemas.filesystem import (
    LocalMountConfig,
    MountFingerprintMaterial,
    MountProviderType,
    MountResolutionResult,
    ResolvedLocalMount,
    build_mount_fingerprint,
)

logger = logging.getLogger(__name__)

_MOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_LOCAL_MOUNT_WORKSPACE_ROOT = "/workspace/.poco-local"
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


class MountProvider(Protocol):
    """Provider abstraction for local mount resolution."""

    provider_type: MountProviderType

    def resolve(
        self,
        mounts: list[LocalMountConfig],
        session_id: str | None = None,
    ) -> list[ResolvedLocalMount]:
        """Resolve user-visible local mounts into host/container bind targets."""
        ...


class DirectBindMountProvider:
    """Local deployment provider backed by Docker bind mounts."""

    provider_type: MountProviderType = "direct_bind"

    def resolve(
        self,
        mounts: list[LocalMountConfig],
        session_id: str | None = None,
    ) -> list[ResolvedLocalMount]:
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        resolved: list[ResolvedLocalMount] = []
        for mount in mounts:
            mount_id = _normalize_mount_id(mount.id)
            if mount_id in seen_ids:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Duplicate local mount id: {mount_id}",
                )
            seen_ids.add(mount_id)

            normalized_path = _normalize_existing_directory_path(mount.host_path)
            if normalized_path in seen_paths:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Duplicate local mount path: {normalized_path}",
                )
            seen_paths.add(normalized_path)
            resolved.append(
                ResolvedLocalMount(
                    id=mount_id,
                    name=mount.name.strip(),
                    source_path=normalized_path,
                    container_path=f"{_LOCAL_MOUNT_WORKSPACE_ROOT}/{mount_id}",
                    access_mode=mount.access_mode,
                    provider_type=self.provider_type,
                )
            )

        return resolved


class LocalMountService:
    """Resolve local mount config into runtime metadata for the manager."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._provider: MountProvider = DirectBindMountProvider()

    def resolve(
        self,
        config: dict[str, Any] | None,
        session_id: str | None = None,
    ) -> MountResolutionResult:
        normalized_config = dict(config or {})
        filesystem_mode = self._normalize_filesystem_mode(
            normalized_config.get("filesystem_mode")
        )

        mounts = self._parse_local_mounts(normalized_config.get("local_mounts"))
        if filesystem_mode != "local_mount":
            mounts = []

        if filesystem_mode == "local_mount" and not mounts:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="filesystem_mode=local_mount requires at least one local mount",
            )

        resolved_mounts = self._provider.resolve(mounts, session_id=session_id)
        fingerprint = build_mount_fingerprint(
            [
                MountFingerprintMaterial(
                    provider_type=mount.provider_type,
                    normalized_source_path=mount.source_path,
                    access_mode=mount.access_mode,
                    container_path=mount.container_path,
                )
                for mount in resolved_mounts
            ]
        )
        logger.info(
            "mount_resolve",
            extra={
                "filesystem_mode": filesystem_mode,
                "mount_count": len(resolved_mounts),
            },
        )
        return MountResolutionResult(
            resolved_mounts=resolved_mounts,
            mount_fingerprint=fingerprint,
        )

    def build_runtime_config(
        self,
        config: dict[str, Any] | None,
        session_id: str | None = None,
    ) -> tuple[dict[str, Any], MountResolutionResult]:
        normalized = dict(config or {})
        resolution = self.resolve(normalized, session_id=session_id)
        filesystem_mode = self._normalize_filesystem_mode(
            normalized.get("filesystem_mode")
        )
        normalized["filesystem_mode"] = filesystem_mode
        normalized["mount_fingerprint"] = resolution.mount_fingerprint
        normalized["resolved_local_mounts"] = [
            mount.model_dump(mode="json") for mount in resolution.resolved_mounts
        ]
        return normalized, resolution

    @staticmethod
    def _normalize_filesystem_mode(value: Any) -> str:
        return "local_mount" if value == "local_mount" else "sandbox"

    @staticmethod
    def _parse_local_mounts(value: Any) -> list[LocalMountConfig]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="local_mounts must be a list",
            )
        mounts: list[LocalMountConfig] = []
        for item in value:
            try:
                mounts.append(LocalMountConfig.model_validate(item))
            except Exception as exc:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Invalid local_mounts entry: {exc}",
                ) from exc
        return mounts


def _normalize_mount_id(value: str) -> str:
    mount_id = value.strip()
    if not _MOUNT_ID_PATTERN.fullmatch(mount_id):
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=(
                "local_mount id must match [A-Za-z0-9._-] and cannot contain "
                "path separators"
            ),
        )
    return mount_id


def _normalize_existing_directory_path(value: str) -> str:
    """Normalize a host path for bind mounting without probing the filesystem."""
    raw = value.strip()
    path = Path(raw)
    if not path.is_absolute():
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Local mount path must be absolute: {raw}",
        )

    normalized = path.resolve(strict=False)
    normalized_text = str(normalized)
    if normalized_text in _FORBIDDEN_ROOTS:
        raise AppException(
            error_code=ErrorCode.BAD_REQUEST,
            message=f"Refusing to mount restricted directory: {normalized_text}",
        )
    return normalized_text
