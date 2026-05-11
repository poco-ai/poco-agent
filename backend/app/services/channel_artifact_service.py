import uuid
from pathlib import PurePosixPath
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_session import AgentSession
from app.models.channel_artifact import ChannelArtifact
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.channel_artifact_repository import ChannelArtifactRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.session_repository import SessionRepository
from app.schemas.channel_artifact import (
    AgentChannelArtifactListResponse,
    AgentChannelArtifactMetadata,
    AgentChannelArtifactReadResponse,
    AgentChannelArtifactSearchResponse,
)
from app.schemas.workspace import FileNode
from app.services.server_channel_access import require_channel_member_access
from app.services.server_member_service import require_server_member
from app.services.storage_service import S3StorageService
from app.utils.workspace import build_workspace_file_nodes
from app.utils.workspace_manifest import (
    build_nodes_from_file_entries,
    extract_manifest_files,
    normalize_manifest_path,
)


class ChannelArtifactService:
    DEFAULT_READ_BYTES = 32 * 1024
    MAX_READ_BYTES = 64 * 1024
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".json",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".csv",
    }

    def __init__(self) -> None:
        self._storage = S3StorageService()

    @staticmethod
    def _parse_scope_ids(
        db_session: AgentSession,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None] | None:
        config_snapshot = db_session.config_snapshot or {}
        server_id_raw = str(config_snapshot.get("server_id") or "").strip()
        channel_id_raw = str(config_snapshot.get("channel_id") or "").strip()
        agent_identity_id_raw = str(
            config_snapshot.get("agent_identity_id") or ""
        ).strip()
        if not server_id_raw or not channel_id_raw:
            return None
        server_id = uuid.UUID(server_id_raw)
        channel_id = uuid.UUID(channel_id_raw)
        agent_identity_id = (
            uuid.UUID(agent_identity_id_raw) if agent_identity_id_raw else None
        )
        return server_id, channel_id, agent_identity_id

    @staticmethod
    def _resolve_object_key(
        file_entry: dict[str, Any],
        *,
        workspace_files_prefix: str,
    ) -> str | None:
        object_key = (
            file_entry.get("key")
            or file_entry.get("object_key")
            or file_entry.get("oss_key")
            or file_entry.get("s3_key")
        )
        if object_key:
            return str(object_key)
        normalized_path = normalize_manifest_path(file_entry.get("path"))
        if not normalized_path:
            return None
        prefix = workspace_files_prefix.rstrip("/")
        if not prefix:
            return None
        return f"{prefix}/{normalized_path.lstrip('/')}"

    @staticmethod
    def _is_publishable_path(path: str) -> bool:
        normalized = normalize_manifest_path(path)
        if not normalized:
            return False
        return not (
            normalized.startswith("/agent_state/")
            or normalized.startswith("/.poco-local/")
        )

    @classmethod
    def _is_text_artifact(cls, artifact: ChannelArtifact) -> bool:
        mime_type = artifact.mime_type or ""
        if mime_type.startswith("text/"):
            return True
        suffix = PurePosixPath(artifact.logical_path).suffix.lower()
        return suffix in cls.TEXT_EXTENSIONS

    @classmethod
    def _content_kind(cls, artifact: ChannelArtifact) -> str:
        return "text" if cls._is_text_artifact(artifact) else "binary"

    @classmethod
    def _metadata(cls, artifact: ChannelArtifact) -> AgentChannelArtifactMetadata:
        return AgentChannelArtifactMetadata(
            artifact_id=artifact.id,
            logical_path=artifact.logical_path,
            display_name=artifact.display_name,
            source_kind=artifact.source_kind,
            source_session_id=artifact.source_session_id,
            agent_identity_id=artifact.agent_identity_id,
            publisher_user_id=artifact.publisher_user_id,
            mime_type=artifact.mime_type,
            size_bytes=artifact.size_bytes,
            is_previewable=artifact.is_previewable,
            content_kind=cls._content_kind(artifact),
            created_at=getattr(artifact, "created_at", None),
            updated_at=getattr(artifact, "updated_at", None),
        )

    @staticmethod
    def _resolve_runtime_scope(
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        db_session = SessionRepository.get_by_id(db, session_id)
        if db_session is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Session not found: {session_id}",
            )

        snapshot = db_session.config_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        try:
            server_id = uuid.UUID(str(snapshot.get("server_id")))
            channel_id = uuid.UUID(str(snapshot.get("channel_id")))
            agent_identity_id = uuid.UUID(str(snapshot.get("agent_identity_id")))
        except (TypeError, ValueError):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session is missing channel artifact runtime context",
            )

        membership = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel_id=channel_id,
            agent_identity_id=agent_identity_id,
        )
        if membership is None:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Agent is not a member of this channel",
            )
        return server_id, channel_id, agent_identity_id

    @staticmethod
    def _normalize_logical_path_for_read(logical_path: str | None) -> str | None:
        normalized = normalize_manifest_path(logical_path)
        if not normalized:
            return None
        if normalized.startswith("/workspace/") or normalized == "/workspace":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=(
                    "logical_path identifies a published channel artifact, "
                    "not a /workspace filesystem path"
                ),
            )
        return normalized

    def sync_session_workspace_artifacts(
        self,
        db: Session,
        db_session: AgentSession,
    ) -> int:
        if (db_session.workspace_export_status or "").strip().lower() != "ready":
            return 0
        if (
            not db_session.workspace_manifest_key
            or not db_session.workspace_files_prefix
        ):
            return 0

        scope = self._parse_scope_ids(db_session)
        if scope is None:
            return 0
        server_id, channel_id, agent_identity_id = scope

        manifest = self._storage.get_manifest(db_session.workspace_manifest_key)
        artifacts: list[ChannelArtifact] = []
        for file_entry in extract_manifest_files(manifest):
            normalized_path = normalize_manifest_path(file_entry.get("path"))
            if not normalized_path or not self._is_publishable_path(normalized_path):
                continue
            object_key = self._resolve_object_key(
                file_entry,
                workspace_files_prefix=db_session.workspace_files_prefix,
            )
            if not object_key:
                continue
            artifacts.append(
                ChannelArtifact(
                    server_id=server_id,
                    channel_id=channel_id,
                    source_session_id=db_session.id,
                    agent_identity_id=agent_identity_id,
                    publisher_user_id=db_session.user_id,
                    source_kind="workspace_export",
                    logical_path=normalized_path,
                    display_name=PurePosixPath(normalized_path).name,
                    object_key=object_key,
                    mime_type=file_entry.get("mimeType") or file_entry.get("mime_type"),
                    size_bytes=file_entry.get("size"),
                    is_previewable=True,
                )
            )

        ChannelArtifactRepository.upsert_many(db, artifacts=artifacts)
        return len(artifacts)

    def list_runtime_artifacts(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> AgentChannelArtifactListResponse:
        _, channel_id, _ = self._resolve_runtime_scope(db, session_id=session_id)
        artifacts = ChannelArtifactRepository.list_by_channel(db, channel_id=channel_id)
        return AgentChannelArtifactListResponse(
            artifacts=[self._metadata(artifact) for artifact in artifacts]
        )

    def read_runtime_artifact(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        artifact_id: uuid.UUID | None = None,
        logical_path: str | None = None,
        max_bytes: int | None = None,
    ) -> AgentChannelArtifactReadResponse:
        _, channel_id, _ = self._resolve_runtime_scope(db, session_id=session_id)
        artifact: ChannelArtifact | None = None
        if artifact_id is not None:
            artifact = ChannelArtifactRepository.get_by_channel_and_id(
                db,
                channel_id=channel_id,
                artifact_id=artifact_id,
            )
        else:
            normalized_path = self._normalize_logical_path_for_read(logical_path)
            if normalized_path is None:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="artifact_id or logical_path is required",
                )
            artifact = ChannelArtifactRepository.get_by_channel_and_path(
                db,
                channel_id=channel_id,
                logical_path=normalized_path,
            )

        if artifact is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Channel artifact not found",
            )

        metadata = self._metadata(artifact)
        if not self._is_text_artifact(artifact):
            return AgentChannelArtifactReadResponse(
                artifact=metadata,
                metadata_only=True,
                reason="binary_or_unsupported_preview",
            )

        read_limit = min(max_bytes or self.DEFAULT_READ_BYTES, self.MAX_READ_BYTES)
        if (
            artifact.size_bytes is not None
            and artifact.size_bytes > self.MAX_READ_BYTES
        ):
            return AgentChannelArtifactReadResponse(
                artifact=metadata,
                metadata_only=True,
                reason="file_too_large",
            )

        content = self._storage.get_text(artifact.object_key)
        truncated = len(content.encode("utf-8")) > read_limit
        if truncated:
            content = content.encode("utf-8")[:read_limit].decode(
                "utf-8",
                errors="ignore",
            )
        return AgentChannelArtifactReadResponse(
            artifact=metadata,
            content=content,
            truncated=truncated,
        )

    def search_runtime_artifacts(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        query: str,
        limit: int = 10,
        include_content: bool = False,
    ) -> AgentChannelArtifactSearchResponse:
        _, channel_id, _ = self._resolve_runtime_scope(db, session_id=session_id)
        normalized_query = query.strip()
        if not normalized_query:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="query must be a non-empty string",
            )

        artifacts = ChannelArtifactRepository.search_by_channel(
            db,
            channel_id=channel_id,
            query=normalized_query,
            limit=limit,
        )
        if include_content and len(artifacts) < limit:
            seen_ids = {artifact.id for artifact in artifacts}
            for artifact in ChannelArtifactRepository.list_by_channel(
                db,
                channel_id=channel_id,
            ):
                if artifact.id in seen_ids or not self._is_text_artifact(artifact):
                    continue
                if (
                    artifact.size_bytes is not None
                    and artifact.size_bytes > self.MAX_READ_BYTES
                ):
                    continue
                try:
                    content = self._storage.get_text(artifact.object_key)
                except Exception:
                    continue
                if normalized_query.lower() in content.lower():
                    artifacts.append(artifact)
                    seen_ids.add(artifact.id)
                    if len(artifacts) >= limit:
                        break

        return AgentChannelArtifactSearchResponse(
            artifacts=[self._metadata(artifact) for artifact in artifacts[:limit]]
        )

    def list_channel_artifact_nodes(
        self,
        db: Session,
        *,
        current_user: Any,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[FileNode]:
        require_channel_member_access(
            db,
            server_id=server_id,
            channel_id=channel_id,
            user_id=current_user.id,
        )
        artifacts = ChannelArtifactRepository.list_by_channel(
            db,
            channel_id=channel_id,
        )

        grouped_entries: dict[str, dict[str, Any]] = {}
        for artifact in artifacts:
            if artifact.agent_identity_id is not None:
                group_key = f"agent:{artifact.agent_identity_id}"
                agent = AgentIdentityRepository.get_by_id(
                    db, artifact.agent_identity_id
                )
                group_name = (
                    agent.display_name
                    if agent is not None and agent.display_name
                    else str(artifact.agent_identity_id)
                )
            else:
                publisher_label = artifact.publisher_user_id or "shared"
                group_key = f"user:{publisher_label}"
                group_name = publisher_label

            group = grouped_entries.setdefault(
                group_key,
                {"name": group_name, "files": [], "url_map": {}},
            )
            relative_path = artifact.logical_path.lstrip("/")
            group["files"].append(
                {
                    "path": relative_path,
                    "key": artifact.object_key,
                    "mimeType": artifact.mime_type,
                    "size": getattr(artifact, "size_bytes", None),
                }
            )
            group["url_map"][normalize_manifest_path(artifact.logical_path)] = (
                self._storage.presign_get(
                    artifact.object_key,
                    response_content_disposition="inline",
                    response_content_type=artifact.mime_type,
                )
            )

        roots: list[FileNode] = []
        for group_key, group in grouped_entries.items():
            raw_nodes = build_nodes_from_file_entries(group["files"])
            url_map = cast(dict[str, str], group["url_map"])

            def build_artifact_url(file_path: str) -> str | None:
                return url_map.get(normalize_manifest_path(file_path) or file_path)

            nodes = build_workspace_file_nodes(
                raw_nodes,
                file_url_builder=build_artifact_url,
            )
            roots.append(
                FileNode(
                    id=f"group/{group_key}",
                    name=str(group["name"]),
                    type="folder",
                    path=f"group/{group_key}",
                    children=nodes,
                )
            )
        return roots
