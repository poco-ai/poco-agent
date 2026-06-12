from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_identity import AgentIdentity
from app.schemas.workspace import FileNode
from app.services.agent_state_bootstrap_service import DEFAULT_AGENT_STATE_BASE_DIR
from app.services.server_member_service import require_server_owner
from app.utils.mime import guess_mime_type


class AgentStateBrowserService:
    """Browse owner-visible persistent files for a server agent."""

    BASE_DIR = DEFAULT_AGENT_STATE_BASE_DIR
    PREFIX = "agent-state"

    def _require_owner_agent(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
        current_user_id: str,
    ) -> AgentIdentity:
        require_server_owner(db, server_id, current_user_id)
        from app.repositories.agent_identity_repository import AgentIdentityRepository

        agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent is None or agent.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )
        if agent.persistent_state is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent persistent state is not initialized",
            )
        return agent

    def list_files(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
        current_user_id: str,
        max_depth: int = 8,
        max_entries: int = 4000,
    ) -> list[FileNode]:
        agent = self._require_owner_agent(
            db,
            server_id=server_id,
            agent_identity_id=agent_identity_id,
            current_user_id=current_user_id,
        )
        persistent_state = agent.persistent_state
        if persistent_state is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent persistent state is not initialized",
            )
        root_relative = Path(persistent_state.state_root_path)
        root_path = (self.BASE_DIR / root_relative).resolve(strict=False)
        counter = {"count": 0}
        return [
            FileNode(
                id=f"{self.PREFIX}/{agent_identity_id}",
                name=root_path.name,
                type="folder",
                path=f"{self.PREFIX}/{agent_identity_id}",
                source="workspace",
                children=self._build_dir_nodes(
                    root_path=root_path,
                    current=root_path,
                    agent_identity_id=agent_identity_id,
                    max_depth=max_depth,
                    max_entries=max_entries,
                    counter=counter,
                    depth=0,
                ),
            )
        ]

    def resolve_file(
        self,
        db: Session,
        *,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
        current_user_id: str,
        path: str,
    ) -> Path:
        agent = self._require_owner_agent(
            db,
            server_id=server_id,
            agent_identity_id=agent_identity_id,
            current_user_id=current_user_id,
        )
        persistent_state = agent.persistent_state
        if persistent_state is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent persistent state is not initialized",
            )
        root_path = (self.BASE_DIR / Path(persistent_state.state_root_path)).resolve(
            strict=False
        )
        target = self._resolve_candidate(
            root_path=root_path,
            agent_identity_id=agent_identity_id,
            path=path,
        )
        if not target.is_file():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent state file not found",
            )
        return target

    def _resolve_candidate(
        self,
        *,
        root_path: Path,
        agent_identity_id: uuid.UUID,
        path: str,
    ) -> Path:
        prefix = f"{self.PREFIX}/{agent_identity_id}"
        clean = (path or "").strip().strip("/")
        if clean == prefix:
            return root_path
        if not clean.startswith(f"{prefix}/"):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid agent state path",
            )
        relative_path = clean.removeprefix(f"{prefix}/")
        candidate = (root_path / relative_path).resolve(strict=False)
        try:
            candidate.relative_to(root_path)
        except Exception as exc:
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Path escapes the agent state root",
            ) from exc
        if not candidate.exists():
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message="Agent state path not found",
            )
        return candidate

    @classmethod
    def _build_dir_nodes(
        cls,
        *,
        root_path: Path,
        current: Path,
        agent_identity_id: uuid.UUID,
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
            node_path = f"{cls.PREFIX}/{agent_identity_id}/{relative_path}"
            counter["count"] += 1

            if entry.is_dir():
                nodes.append(
                    FileNode(
                        id=node_path,
                        name=entry.name,
                        type="folder",
                        path=node_path,
                        source="workspace",
                        children=cls._build_dir_nodes(
                            root_path=root_path,
                            current=entry,
                            agent_identity_id=agent_identity_id,
                            max_depth=max_depth,
                            max_entries=max_entries,
                            counter=counter,
                            depth=depth + 1,
                        ),
                    )
                )
                continue

            nodes.append(
                FileNode(
                    id=node_path,
                    name=entry.name,
                    type="file",
                    path=node_path,
                    source="workspace",
                    mimeType=guess_mime_type(entry.name),
                )
            )

        return nodes
