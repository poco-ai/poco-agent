import json
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, field_validator


FilesystemMode = Literal["sandbox", "local_mount"]
LocalMountAccessMode = Literal["ro", "rw"]
DeploymentMode = Literal["local", "cloud"]
MountProviderType = Literal["direct_bind", "bridge_live_mount"]
LocalFilesystemHelperStatus = Literal[
    "available",
    "not_running",
    "permission_denied",
    "bridge_unreachable",
]


class LocalMountConfig(BaseModel):
    """User-visible local filesystem authorization entry."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    host_path: str = Field(min_length=1)
    access_mode: LocalMountAccessMode = "ro"

    @field_validator("id", "name", "host_path")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty")
        return normalized


class ResolvedLocalMount(BaseModel):
    """Internal resolved local mount metadata for runtime execution."""

    id: str
    name: str
    source_path: str
    container_path: str
    access_mode: LocalMountAccessMode
    provider_type: MountProviderType


class MountFingerprintMaterial(BaseModel):
    """Canonical fingerprint payload for a single resolved mount."""

    deployment_mode: DeploymentMode
    provider_type: MountProviderType
    normalized_source_path: str
    access_mode: LocalMountAccessMode
    container_path: str


class MountResolutionResult(BaseModel):
    """Internal mount resolution output."""

    deployment_mode: DeploymentMode
    provider_type: MountProviderType
    resolved_mounts: list[ResolvedLocalMount] = Field(default_factory=list)
    mount_fingerprint: str


class LocalFilesystemSupport(BaseModel):
    """Frontend-facing local filesystem capability summary."""

    deployment_mode: DeploymentMode
    helper_status: LocalFilesystemHelperStatus
    helper_message: str | None = None
    local_mount_available: bool


def build_mount_fingerprint(
    entries: list[MountFingerprintMaterial],
) -> str:
    """Build a stable fingerprint from normalized mount metadata."""
    serialized = [
        entry.model_dump(mode="json")
        for entry in sorted(entries, key=lambda item: item.container_path)
    ]
    payload = json.dumps(serialized, ensure_ascii=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()
