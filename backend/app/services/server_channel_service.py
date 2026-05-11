import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.models.server_channel_agent_member import ServerChannelAgentMember
from app.models.server_channel_member import ServerChannelMember
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_agent_member_repository import (
    ServerChannelAgentMemberRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.repositories.server_repository import ServerRepository
from app.schemas.server_channel import (
    DirectMessageCreateRequest,
    ServerChannelMemberAddRequest,
    ServerChannelCreateRequest,
    ServerChannelMemberResponse,
    ServerChannelResponse,
    ServerChannelUpdateRequest,
)
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_member_service import (
    require_server_admin,
    require_server_member,
    require_server_owner,
)
from app.services.server_channel_event_service import (
    ChannelEventActor,
    ChannelEventTarget,
    create_channel_event_message,
)
from app.services.user_public_profile_service import list_user_public_profiles_by_id


class ServerChannelService:
    @staticmethod
    def _build_channel_member_response(
        membership: ServerChannelMember,
        *,
        user_profiles: dict[str, UserPublicProfileResponse],
    ) -> ServerChannelMemberResponse:
        return ServerChannelMemberResponse.model_validate(membership).model_copy(
            update={"user": user_profiles.get(membership.user_id)}
        )

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "channel"

    @classmethod
    def _unique_slug(cls, db: Session, server_id: uuid.UUID, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while (
            ServerChannelRepository.get_by_server_slug(db, server_id, slug) is not None
        ):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    @classmethod
    def _unique_slug_for_channel(
        cls,
        db: Session,
        server_id: uuid.UUID,
        base_slug: str,
        channel_id: uuid.UUID,
    ) -> str:
        slug = base_slug
        suffix = 2
        while (
            ServerChannelRepository.get_by_server_slug(
                db,
                server_id,
                slug,
                exclude_channel_id=channel_id,
            )
            is not None
        ):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    @staticmethod
    def _build_channel_response(channel: ServerChannel) -> ServerChannelResponse:
        return ServerChannelResponse.model_validate(channel).model_copy(
            update={"is_system_channel": channel.system_channel_type is not None}
        )

    @staticmethod
    def _user_label(user: User) -> str:
        return user.display_name or user.primary_email or user.id

    @staticmethod
    def _profile_label(
        profiles: dict[str, UserPublicProfileResponse],
        user_id: str,
    ) -> str:
        profile = profiles.get(user_id)
        if profile is not None and profile.display_name:
            return profile.display_name
        return user_id

    @staticmethod
    def _ensure_mutable_channel(channel: ServerChannel) -> None:
        if channel.system_channel_type is not None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="System channels cannot be modified",
            )

    def list_channels(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
    ) -> list[ServerChannelResponse]:
        require_server_member(db, server_id, current_user.id)
        channels = ServerChannelRepository.list_by_server_for_user(
            db,
            server_id,
            current_user.id,
        )
        return [self._build_channel_response(item) for item in channels]

    def create_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        request: ServerChannelCreateRequest,
    ) -> ServerChannelResponse:
        require_server_member(db, server_id, current_user.id)
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )

        name = request.name.strip()
        if not name:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Channel name cannot be empty",
            )
        channel = ServerChannelRepository.create(
            db,
            ServerChannel(
                server_id=server.id,
                name=name,
                slug=self._unique_slug(db, server.id, self._slugify(name)),
                description=request.description.strip()
                if request.description is not None
                else None,
                conversation_type="channel",
                visibility=request.visibility,
                created_by=current_user.id,
            ),
        )
        db.flush()
        member_user_ids = {
            item.strip() for item in request.member_user_ids if item.strip()
        }
        member_user_ids.discard(current_user.id)
        for user_id in member_user_ids:
            server_member = ServerMemberRepository.get_by_server_and_user(
                db,
                server.id,
                user_id,
            )
            if server_member is None or server_member.status != "active":
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"User is not an active server member: {user_id}",
                )
        agent_identity_ids = set(request.agent_identity_ids)
        for agent_identity_id in agent_identity_ids:
            agent_identity = AgentIdentityRepository.get_by_id(db, agent_identity_id)
            if (
                agent_identity is None
                or agent_identity.server_id != server.id
                or agent_identity.removed_at is not None
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Agent identity is not in this server: {agent_identity_id}",
                )
        ServerChannelMemberRepository.create(
            db,
            ServerChannelMember(
                channel=channel,
                user_id=current_user.id,
                role="owner",
                status="active",
            ),
        )
        for user_id in member_user_ids:
            ServerChannelMemberRepository.create(
                db,
                ServerChannelMember(
                    channel=channel,
                    user_id=user_id,
                    role="member",
                    status="active",
                ),
            )
        for agent_identity_id in agent_identity_ids:
            ServerChannelAgentMemberRepository.create(
                db,
                ServerChannelAgentMember(
                    channel_id=channel.id,
                    agent_identity_id=agent_identity_id,
                    role="member",
                    status="active",
                ),
            )
        db.commit()
        db.refresh(channel)
        return self._build_channel_response(channel)

    def archive_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> ServerChannelResponse:
        require_server_admin(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        self._ensure_mutable_channel(channel)
        channel.archived_at = datetime.now(UTC)
        db.commit()
        return self._build_channel_response(channel)

    def update_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        request: ServerChannelUpdateRequest,
    ) -> ServerChannelResponse:
        require_server_admin(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        self._ensure_mutable_channel(channel)

        if request.name is not None:
            name = request.name.strip()
            if not name:
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Channel name cannot be empty",
                )
            if name != channel.name:
                channel.name = name
                channel.slug = self._unique_slug_for_channel(
                    db,
                    server_id,
                    self._slugify(name),
                    channel.id,
                )

        if request.description is not None:
            description = request.description.strip()
            channel.description = description or None

        db.commit()
        db.refresh(channel)
        return self._build_channel_response(channel)

    def delete_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> None:
        require_server_admin(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        self._ensure_mutable_channel(channel)
        ServerChannelRepository.delete(db, channel)
        db.commit()

    def list_channel_members(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> list[ServerChannelMemberResponse]:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        if channel.visibility != "public":
            membership = ServerChannelMemberRepository.get_by_channel_and_user(
                db,
                channel_id,
                current_user.id,
            )
            if membership is None or membership.status != "active":
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Private channel membership is required",
                )
        memberships = ServerChannelMemberRepository.list_by_channel(db, channel_id)
        user_profiles = list_user_public_profiles_by_id(
            db,
            [membership.user_id for membership in memberships],
        )
        return [
            self._build_channel_member_response(
                membership,
                user_profiles=user_profiles,
            )
            for membership in memberships
        ]

    def add_channel_member(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        request: ServerChannelMemberAddRequest,
    ) -> ServerChannelMemberResponse:
        require_server_admin(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )

        target_user_id = request.user_id.strip()
        if not target_user_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Channel member user id cannot be empty",
            )
        server_membership = ServerMemberRepository.get_by_server_and_user(
            db,
            server_id,
            target_user_id,
        )
        if server_membership is None or server_membership.status != "active":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Channel member must be an active server member",
            )

        membership = ServerChannelMemberRepository.get_by_channel_and_user(
            db,
            channel_id,
            target_user_id,
        )
        should_emit_joined_event = membership is None or membership.status != "active"
        if membership is None:
            membership = ServerChannelMemberRepository.create(
                db,
                ServerChannelMember(
                    channel_id=channel.id,
                    user_id=target_user_id,
                    role=request.role or "member",
                    status="active",
                ),
            )
        else:
            membership.role = request.role or membership.role
            membership.status = "active"
        db.flush()
        user_profiles = list_user_public_profiles_by_id(db, [membership.user_id])
        if should_emit_joined_event:
            target_label = self._profile_label(user_profiles, target_user_id)
            create_channel_event_message(
                db,
                channel_id=channel.id,
                event_type="channel.member_joined",
                actor=ChannelEventActor(
                    actor_type="user",
                    actor_user_id=current_user.id,
                    actor_label=self._user_label(current_user),
                ),
                target=ChannelEventTarget(
                    target_user_id=target_user_id,
                    target_label=target_label,
                ),
                content={
                    "membership_id": membership.id,
                    "join_reason": "admin_added",
                },
                text_preview=f"{target_label} joined {channel.name}",
            )
        db.commit()
        db.refresh(membership)
        return self._build_channel_member_response(
            membership,
            user_profiles=user_profiles,
        )

    def remove_channel_member(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        membership_id: int,
    ) -> None:
        require_server_owner(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        membership = ServerChannelMemberRepository.get_by_id(db, membership_id)
        if membership is None or membership.channel_id != channel.id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel membership not found: {membership_id}",
            )
        if membership.role == "owner":
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Channel owner cannot be removed",
            )
        ServerChannelMemberRepository.delete(db, membership)
        db.commit()

    def join_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> ServerChannelMemberResponse:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        if channel.visibility != "public":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Private channels require an invitation",
            )
        membership = ServerChannelMemberRepository.get_by_channel_and_user(
            db,
            channel_id,
            current_user.id,
        )
        should_emit_joined_event = membership is None or membership.status != "active"
        if membership is None:
            membership = ServerChannelMemberRepository.create(
                db,
                ServerChannelMember(
                    channel_id=channel.id,
                    user_id=current_user.id,
                    role="member",
                    status="active",
                ),
            )
        else:
            membership.status = "active"
        db.flush()
        user_profiles = list_user_public_profiles_by_id(db, [membership.user_id])
        if should_emit_joined_event:
            user_label = self._user_label(current_user)
            create_channel_event_message(
                db,
                channel_id=channel.id,
                event_type="channel.member_joined",
                actor=ChannelEventActor(
                    actor_type="user",
                    actor_user_id=current_user.id,
                    actor_label=user_label,
                ),
                target=ChannelEventTarget(
                    target_user_id=current_user.id,
                    target_label=user_label,
                ),
                content={
                    "membership_id": membership.id,
                    "join_reason": "self_join",
                },
                text_preview=f"{user_label} joined {channel.name}",
            )
        db.commit()
        db.refresh(membership)
        return self._build_channel_member_response(
            membership,
            user_profiles=user_profiles,
        )

    def leave_channel(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> None:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        self._ensure_mutable_channel(channel)
        membership = ServerChannelMemberRepository.get_by_channel_and_user(
            db,
            channel_id,
            current_user.id,
        )
        if membership is not None:
            if membership.role == "owner":
                ServerChannelRepository.delete(db, channel)
                db.commit()
                return
            membership.status = "left"
            db.commit()

    def create_direct_message(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        request: DirectMessageCreateRequest,
    ) -> ServerChannelResponse:
        require_server_member(db, server_id, current_user.id)
        server = ServerRepository.get_by_id(db, server_id)
        if server is None:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Server not found: {server_id}",
            )

        if bool(request.target_user_id) == bool(request.target_agent_identity_id):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Exactly one DM target must be provided",
            )

        direct_user_id = request.target_user_id
        direct_agent_identity_id = request.target_agent_identity_id

        if direct_user_id:
            membership = ServerMemberRepository.get_by_server_and_user(
                db,
                server_id,
                direct_user_id,
            )
            if membership is None or membership.status != "active":
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="DM target user must be an active server member",
                )

        if direct_agent_identity_id:
            agent_identity = AgentIdentityRepository.get_by_id(
                db,
                direct_agent_identity_id,
            )
            if (
                agent_identity is None
                or agent_identity.server_id != server_id
                or agent_identity.removed_at is not None
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="DM target agent must belong to the same server",
                )

        existing = ServerChannelRepository.get_direct_message(
            db,
            server_id=server_id,
            direct_user_id=direct_user_id,
            direct_agent_identity_id=direct_agent_identity_id,
        )
        if existing is not None:
            return self._build_channel_response(existing)

        slug_seed = direct_user_id or str(direct_agent_identity_id)
        slug = self._unique_slug(db, server.id, self._slugify(f"dm-{slug_seed}"))
        name = (
            f"DM {direct_user_id}"
            if direct_user_id
            else f"DM {str(direct_agent_identity_id)[:8]}"
        )
        channel = ServerChannelRepository.create(
            db,
            ServerChannel(
                server_id=server.id,
                name=name,
                slug=slug,
                conversation_type="direct_message",
                visibility="private",
                direct_user_id=direct_user_id,
                direct_agent_identity_id=direct_agent_identity_id,
                created_by=current_user.id,
            ),
        )
        db.flush()
        ServerChannelMemberRepository.create(
            db,
            ServerChannelMember(
                channel=channel,
                user_id=current_user.id,
                role="owner",
                status="active",
            ),
        )
        if direct_user_id:
            ServerChannelMemberRepository.create(
                db,
                ServerChannelMember(
                    channel=channel,
                    user_id=direct_user_id,
                    role="member",
                    status="active",
                ),
            )
        if direct_agent_identity_id:
            ServerChannelAgentMemberRepository.create(
                db,
                ServerChannelAgentMember(
                    channel_id=channel.id,
                    agent_identity_id=direct_agent_identity_id,
                    role="member",
                    status="active",
                ),
            )
        db.commit()
        db.refresh(channel)
        return self._build_channel_response(channel)
