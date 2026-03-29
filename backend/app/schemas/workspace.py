from typing import Any, Literal

from app.schemas.filesystem import LocalMountAccessMode

from pydantic import BaseModel

FileSource = Literal["workspace", "local_mount"]


class FileNode(BaseModel):
    """Workspace file node for UI browsing."""

    id: str
    name: str
    type: Literal["file", "folder"]
    path: str
    children: list["FileNode"] | None = None
    url: str | None = None
    mimeType: str | None = None
    oss_status: str | None = None
    oss_meta: dict[str, Any] | None = None
    source: FileSource = "workspace"
    mount_id: str | None = None
    access_mode: LocalMountAccessMode | None = None


class WorkspaceArchiveResponse(BaseModel):
    """Workspace archive download response."""

    url: str | None = None
    filename: str


class SubmitSkillRequest(BaseModel):
    """Submit a workspace folder for skill creation review."""

    folder_path: str
    skill_name: str | None = None
    workspace_files_prefix: str | None = None


class SubmitSkillResponse(BaseModel):
    """Pending skill submission result."""

    pending_id: str
    status: str
