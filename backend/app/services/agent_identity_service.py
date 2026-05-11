import uuid
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_identity import AgentIdentity
from app.models.agent_persistent_state import AgentPersistentState
from app.models.server_channel_agent_member import ServerChannelAgentMember
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.agent_persistent_state_repository import (
    AgentPersistentStateRepository,
)
from app.repositories.preset_repository import PresetRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.server_channel_repository import ServerChannelRepository
from app.repositories.session_queue_item_repository import SessionQueueItemRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.agent_identity import (
    AgentIdentityCreateRequest,
    AgentIdentityResponse,
    AgentIdentityUpdateRequest,
    ChannelAgentMemberCreateRequest,
    ChannelAgentMemberResponse,
)
from app.services.agent_state_bootstrap_service import ensure_agent_state_bootstrap
from app.services.server_member_service import (
    require_server_admin,
    require_server_member,
    require_server_owner,
)
from app.services.session_service import SessionService


class AgentIdentityService:
    def __init__(self, *, session_service: SessionService | None = None) -> None:
        self._session_service = session_service or SessionService()

    @staticmethod
    def _to_agent_response(agent_identity: AgentIdentity) -> AgentIdentityResponse:
        return AgentIdentityResponse.model_validate(agent_identity)

    @staticmethod
    def _to_channel_member_response(
        membership: ServerChannelAgentMember,
    ) -> ChannelAgentMemberResponse:
        return ChannelAgentMemberResponse.model_validate(membership)

    @staticmethod
    def _build_state_paths(agent_identity_id: uuid.UUID) -> dict[str, str]:
        root = f"agents/{agent_identity_id}"
        return {
            "state_root_path": root,
            "profile_path": f"{root}/profile.json",
            "memory_path": f"{root}/MEMORY.md",
            "notes_dir_path": f"{root}/notes",
            "state_dir_path": f"{root}/state",
            "artifacts_dir_path": f"{root}/artifacts",
        }

    @staticmethod
    def _unique_handle(db: Session, server_id: uuid.UUID, value: str) -> str:
        base = AgentIdentity.slugify_handle(value)
        handle = base
        suffix = 2
        while AgentIdentityRepository.get_by_server_and_handle(db, server_id, handle):
            handle = f"{base}-{suffix}"
            suffix += 1
        return handle

    @staticmethod
    def _is_removed(agent_identity: AgentIdentity) -> bool:
        return agent_identity.removed_at is not None

    @staticmethod
    def _resolve_preset_for_user(db: Session, user_id: str, preset_id: int):
        preset = PresetRepository.get_visible_by_id(db, preset_id, user_id)
        if preset is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Preset not found: {preset_id}",
            )
        return preset

    def list_agents(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> list[AgentIdentityResponse]:
        require_server_member(db, server_id, current_user.id)
        return [
            self._to_agent_response(item)
            for item in AgentIdentityRepository.list_by_server(
                db,
                server_id,
                include_removed=False,
            )
        ]

    def get_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> AgentIdentityResponse:
        require_server_member(db, server_id, current_user.id)
        agent_identity = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent_identity is None or agent_identity.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )
        return self._to_agent_response(agent_identity)

    def create_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        request: AgentIdentityCreateRequest,
    ) -> AgentIdentityResponse:
        require_server_admin(db, server_id, current_user.id)
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )

        preset = self._resolve_preset_for_user(db, current_user.id, request.preset_id)
        display_name = request.display_name.strip()
        if not display_name:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Agent display name must not be empty",
            )
        existing_display_name = AgentIdentityRepository.get_by_server_and_display_name(
            db,
            server.id,
            display_name,
            include_removed=False,
        )
        if existing_display_name is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Agent display name already exists: {display_name}",
            )
        handle_seed = request.handle or request.display_name
        handle = self._unique_handle(db, server.id, handle_seed)
        visual_key = (request.visual_key or "").strip() or preset.visual_key
        agent_identity = AgentIdentityRepository.create(
            db,
            AgentIdentity(
                server_id=server.id,
                preset_id=preset.id,
                handle=handle,
                display_name=display_name,
                description=(request.description or "").strip() or None,
                visual_key=visual_key,
                visibility=request.visibility.strip() or "server",
                lifecycle_state="active",
                created_by=current_user.id,
                updated_by=current_user.id,
            ),
        )
        db.flush()

        persistent_state = AgentPersistentState(
            agent_identity_id=agent_identity.id,
            runtime_status="idle",
            state_version=1,
            **self._build_state_paths(agent_identity.id),
        )
        AgentPersistentStateRepository.create(
            db,
            persistent_state,
        )
        ensure_agent_state_bootstrap(
            agent_identity=agent_identity,
            persistent_state=persistent_state,
        )
        db.commit()
        db.refresh(agent_identity)
        agent_identity = cast(
            AgentIdentity,
            AgentIdentityRepository.get_by_id(db, agent_identity.id),
        )
        return self._to_agent_response(agent_identity)

    def update_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
        request: AgentIdentityUpdateRequest,
    ) -> AgentIdentityResponse:
        agent_identity = self._require_owner_agent(
            db,
            current_user,
            server_id,
            agent_identity_id,
        )
        if self._is_removed(agent_identity):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Agent identity has been removed: {agent_identity_id}",
            )
        agent_identity.description = (
            request.description.strip() if request.description else None
        )
        agent_identity.updated_by = current_user.id
        db.commit()
        db.refresh(agent_identity)
        return self._to_agent_response(agent_identity)

    def list_channel_agents(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[AgentIdentityResponse]:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )

        memberships = ServerChannelAgentMemberRepository.list_by_channel(db, channel.id)
        agent_responses: list[AgentIdentityResponse] = []
        for membership in memberships:
            if membership.status != "active":
                continue
            agent_identity = AgentIdentityRepository.get_by_id(
                db, membership.agent_identity_id
            )
            if agent_identity is None:
                continue
            if self._is_removed(agent_identity):
                continue
            agent_responses.append(self._to_agent_response(agent_identity))
        return agent_responses

    def add_agent_to_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        request: ChannelAgentMemberCreateRequest,
    ) -> ChannelAgentMemberResponse:
        require_server_admin(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        agent_identity = AgentIdentityRepository.get_by_id(
            db, request.agent_identity_id
        )
        if agent_identity is None or agent_identity.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {request.agent_identity_id}",
            )
        if self._is_removed(agent_identity):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Agent identity has been removed: {request.agent_identity_id}",
            )
        existing = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel.id,
            agent_identity.id,
        )
        if existing is not None:
            if existing.status != "active":
                existing.status = "active"
                existing.role = request.role
                db.commit()
                db.refresh(existing)
            return self._to_channel_member_response(existing)

        membership = ServerChannelAgentMemberRepository.create(
            db,
            ServerChannelAgentMember(
                channel_id=channel.id,
                agent_identity_id=agent_identity.id,
                role=request.role,
                status="active",
            ),
        )
        db.commit()
        db.refresh(membership)
        return self._to_channel_member_response(membership)

    def remove_agent_from_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> None:
        require_server_owner(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        agent_identity = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent_identity is None or agent_identity.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )
        if self._is_removed(agent_identity):
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )
        membership = ServerChannelAgentMemberRepository.get_by_channel_and_agent(
            db,
            channel.id,
            agent_identity.id,
        )
        if membership is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel agent membership not found: {agent_identity_id}",
            )
        self._cancel_queued_scope(
            db,
            agent_identity_id=agent_identity.id,
            channel_id=channel.id,
        )
        membership.status = "removed"
        db.commit()

    def remove_agent_from_server(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> None:
        agent_identity = self._require_owner_agent(
            db,
            current_user,
            server_id,
            agent_identity_id,
        )
        self._discard_all_tasks(db, agent_identity, reason="Agent removed from server")
        agent_identity.lifecycle_state = "inactive"
        agent_identity.updated_by = current_user.id
        agent_identity.removed_at = datetime.now(UTC)
        agent_identity.removed_by = current_user.id
        if agent_identity.persistent_state is not None:
            agent_identity.persistent_state.runtime_status = "idle"
            agent_identity.persistent_state.active_session_id = None
            agent_identity.persistent_state.active_task_id = None
        self._cancel_queued_scope(
            db,
            agent_identity_id=agent_identity.id,
            channel_id=None,
        )
        for membership in ServerChannelAgentMemberRepository.list_by_agent(
            db,
            agent_identity.id,
        ):
            membership.status = "removed"
        db.commit()

    def restart_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> AgentIdentityResponse:
        agent_identity = self._require_owner_agent(
            db,
            current_user,
            server_id,
            agent_identity_id,
        )
        if self._is_removed(agent_identity):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Agent identity has been removed: {agent_identity_id}",
            )
        self._discard_active_execution(db, agent_identity, reason="Agent restarted")
        agent_identity.lifecycle_state = "active"
        agent_identity.updated_by = current_user.id
        if agent_identity.persistent_state is not None:
            agent_identity.persistent_state.runtime_status = "idle"
            agent_identity.persistent_state.active_session_id = None
            agent_identity.persistent_state.active_task_id = None
        db.commit()
        db.refresh(agent_identity)
        return self._to_agent_response(agent_identity)

    def stop_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> AgentIdentityResponse:
        agent_identity = self._require_owner_agent(
            db,
            current_user,
            server_id,
            agent_identity_id,
        )
        if self._is_removed(agent_identity):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Agent identity has been removed: {agent_identity_id}",
            )
        self._discard_active_execution(db, agent_identity, reason="Agent stopped")
        agent_identity.lifecycle_state = "inactive"
        agent_identity.updated_by = current_user.id
        if agent_identity.persistent_state is not None:
            agent_identity.persistent_state.runtime_status = "idle"
            agent_identity.persistent_state.active_session_id = None
            agent_identity.persistent_state.active_task_id = None
        db.commit()
        db.refresh(agent_identity)
        return self._to_agent_response(agent_identity)

    def _require_owner_agent(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        agent_identity_id: uuid.UUID,
    ) -> AgentIdentity:
        require_server_owner(db, server_id, current_user.id)
        agent_identity = AgentIdentityRepository.get_by_id(db, agent_identity_id)
        if agent_identity is None or agent_identity.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Agent identity not found: {agent_identity_id}",
            )
        return agent_identity

    def _discard_active_execution(
        self,
        db: Session,
        agent_identity: AgentIdentity,
        *,
        reason: str,
    ) -> None:
        persistent_state = agent_identity.persistent_state
        if persistent_state is None or persistent_state.active_session_id is None:
            return
        try:
            self._session_service.cancel_current_execution(
                db,
                persistent_state.active_session_id,
                user_id=agent_identity.created_by,
                reason=reason,
            )
        except AppException as exc:
            if exc.error_code != ErrorCode.BAD_REQUEST:
                raise

    def _discard_all_tasks(
        self,
        db: Session,
        agent_identity: AgentIdentity,
        *,
        reason: str,
    ) -> None:
        persistent_state = agent_identity.persistent_state
        if persistent_state is None or persistent_state.active_session_id is None:
            return
        self._session_service.cancel_session(
            db,
            persistent_state.active_session_id,
            user_id=agent_identity.created_by,
            reason=reason,
        )

    @staticmethod
    def _cancel_queued_scope(
        db: Session,
        *,
        agent_identity_id: uuid.UUID,
        channel_id: uuid.UUID | None,
    ) -> None:
        queue_items = SessionQueueItemRepository.list_active_by_agent_scope(
            db,
            agent_identity_id=agent_identity_id,
            channel_id=channel_id,
            for_update=True,
        )
        for item in queue_items:
            item.status = "canceled"

        placeholders = ServerChannelMessageRepository.list_open_execution_placeholders_by_agent_scope(
            db,
            agent_identity_id=agent_identity_id,
            channel_id=channel_id,
        )
        canceled_queue_item_ids = {str(item.id) for item in queue_items}
        for placeholder in placeholders:
            content = dict(placeholder.content or {})
            queue_item_id = str(content.get("queue_item_id") or "").strip()
            if channel_id is not None and queue_item_id not in canceled_queue_item_ids:
                continue
            content["execution_status"] = "canceled"
            content["summary"] = "Execution canceled."
            placeholder.content = content
            placeholder.text_preview = "Execution canceled."
