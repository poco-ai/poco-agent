import logging
import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.models.server_channel_message import ServerChannelMessage
from app.models.user import User
from app.repositories.agent_identity_repository import AgentIdentityRepository
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.schemas.server_channel_message import (
    ServerChannelMessageCreateRequest,
    ServerChannelMessageContextResponse,
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionGroupResponse,
)
from app.schemas.agent_identity import AgentIdentityResponse
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_agent_trigger_service import ServerAgentTriggerService
from app.services.server_member_service import require_server_member
from app.services.user_public_profile_service import (
    build_user_public_profile,
    list_user_public_profiles_by_id,
)

logger = logging.getLogger(__name__)


class ServerChannelMessageService:
    @staticmethod
    def _build_message_response(
        message: ServerChannelMessage,
        *,
        reply_count: int = 0,
        author_user: UserPublicProfileResponse | None = None,
        author_agent: AgentIdentityResponse | None = None,
        reactions: list[ServerChannelMessageReactionGroupResponse] | None = None,
    ) -> ServerChannelMessageResponse:
        return ServerChannelMessageResponse.model_validate(
            message,
        ).model_copy(
            update={
                "reply_count": reply_count,
                "author_user": author_user,
                "author_agent": author_agent,
                "reactions": reactions or [],
            }
        )

    @staticmethod
    def _message_agent_identity_id(message: ServerChannelMessage) -> uuid.UUID | None:
        content = message.content if isinstance(message.content, dict) else {}
        raw = content.get("agent_identity_id")
        if raw is None:
            return None
        try:
            return uuid.UUID(str(raw))
        except ValueError:
            return None

    @staticmethod
    def _message_agent_handle(message: ServerChannelMessage) -> str | None:
        content = message.content if isinstance(message.content, dict) else {}
        raw = content.get("agent_handle")
        if not isinstance(raw, str):
            return None
        return raw.strip() or None

    def _load_author_agents(
        self,
        db: Session,
        server_id: uuid.UUID,
        messages: list[ServerChannelMessage],
    ) -> dict[uuid.UUID, AgentIdentityResponse]:
        responses: dict[uuid.UUID, AgentIdentityResponse] = {}
        missing_by_handle: list[ServerChannelMessage] = []
        for message in messages:
            if message.message_type != "system":
                continue
            agent_identity_id = self._message_agent_identity_id(message)
            if agent_identity_id is None:
                missing_by_handle.append(message)
                continue
            agent = AgentIdentityRepository.get_by_id(db, agent_identity_id)
            if agent is not None and agent.server_id == server_id:
                responses[message.id] = AgentIdentityResponse.model_validate(agent)

        for message in missing_by_handle:
            handle = self._message_agent_handle(message)
            if not handle:
                continue
            agent = AgentIdentityRepository.get_by_server_and_handle(
                db,
                server_id,
                handle,
                include_removed=True,
            )
            if agent is not None:
                responses[message.id] = AgentIdentityResponse.model_validate(agent)
        return responses

    def _require_channel_access(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> ServerChannel:
        require_server_member(db, server_id, current_user.id)
        channel = ServerChannelRepository.get_by_id(db, channel_id)
        if channel is None or channel.server_id != server_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel not found: {channel_id}",
            )
        if channel.visibility == "private":
            membership = ServerChannelMemberRepository.get_by_channel_and_user(
                db,
                channel.id,
                current_user.id,
            )
            if membership is None or membership.status != "active":
                raise AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="You are not a member of this private channel",
                )
        return channel

    def send_message(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        request: ServerChannelMessageCreateRequest,
    ) -> ServerChannelMessageResponse:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        author_user_id = current_user.id if request.message_type == "user" else None
        thread_root_message_id = request.thread_root_message_id
        if thread_root_message_id is not None:
            root = ServerChannelMessageRepository.get_by_id(db, thread_root_message_id)
            if (
                root is None
                or root.channel_id != channel.id
                or root.thread_root_message_id is not None
            ):
                raise AppException(
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Thread root message is invalid",
                )

        message = ServerChannelMessageRepository.create(
            db,
            ServerChannelMessage(
                channel_id=channel.id,
                author_user_id=author_user_id,
                message_type=request.message_type,
                content=request.content,
                text_preview=request.text_preview,
                thread_root_message_id=thread_root_message_id,
            ),
        )
        db.commit()
        db.refresh(message)
        if request.message_type == "user":
            try:
                ServerAgentTriggerService().trigger_for_channel_message(
                    db,
                    current_user=current_user,
                    server_id=server_id,
                    channel=channel,
                    message=message,
                )
            except Exception:
                db.rollback()
                logger.exception(
                    "server_agent_trigger_failed",
                    extra={
                        "server_id": str(server_id),
                        "channel_id": str(channel.id),
                        "message_id": str(message.id),
                    },
                )
        return self._build_message_response(
            message,
            author_user=build_user_public_profile(current_user)
            if author_user_id
            else None,
        )

    def list_messages(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        *,
        before_message_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ServerChannelMessageResponse]:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        safe_limit = max(1, min(int(limit), 100))
        messages = ServerChannelMessageRepository.list_by_channel(
            db,
            channel.id,
            before_message_id=before_message_id,
            limit=safe_limit,
        )
        author_profiles = list_user_public_profiles_by_id(
            db,
            [
                item.author_user_id
                for item in messages
                if item.author_user_id is not None
            ],
        )
        reply_counts = ServerChannelMessageRepository.count_replies_by_roots(
            db,
            [item.id for item in messages],
        )
        from app.services.server_channel_message_reaction_service import (
            ServerChannelMessageReactionService,
        )

        reactions = ServerChannelMessageReactionService().list_grouped_by_messages(
            db,
            [item.id for item in messages],
            current_user_id=current_user.id,
        )
        author_agents = self._load_author_agents(db, server_id, messages)
        return [
            self._build_message_response(
                item,
                reply_count=reply_counts.get(item.id, 0),
                author_user=author_profiles.get(item.author_user_id or ""),
                author_agent=author_agents.get(item.id),
                reactions=reactions.get(item.id, []),
            )
            for item in messages
        ]

    def get_thread(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        thread_root_message_id: uuid.UUID,
    ) -> ServerChannelThreadResponse:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        root = ServerChannelMessageRepository.get_by_id(db, thread_root_message_id)
        if root is None or root.channel_id != channel.id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Thread not found: {thread_root_message_id}",
            )
        root_id = root.thread_root_message_id or root.id
        if root.thread_root_message_id is not None:
            root = ServerChannelMessageRepository.get_by_id(db, root_id)
            if root is None:
                raise AppException(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Thread not found: {thread_root_message_id}",
                )
        replies = ServerChannelMessageRepository.list_replies(db, root_id)
        all_messages = [root, *replies]
        author_profiles = list_user_public_profiles_by_id(
            db,
            [
                author_user_id
                for author_user_id in [
                    root.author_user_id,
                    *[reply.author_user_id for reply in replies],
                ]
                if author_user_id is not None
            ],
        )
        from app.services.server_channel_message_reaction_service import (
            ServerChannelMessageReactionService,
        )

        reactions = ServerChannelMessageReactionService().list_grouped_by_messages(
            db,
            [item.id for item in all_messages],
            current_user_id=current_user.id,
        )
        author_agents = self._load_author_agents(db, server_id, all_messages)
        return ServerChannelThreadResponse(
            root=self._build_message_response(
                root,
                author_user=author_profiles.get(root.author_user_id or ""),
                author_agent=author_agents.get(root.id),
                reactions=reactions.get(root.id, []),
            ),
            replies=[
                self._build_message_response(
                    item,
                    author_user=author_profiles.get(item.author_user_id or ""),
                    author_agent=author_agents.get(item.id),
                    reactions=reactions.get(item.id, []),
                )
                for item in replies
            ],
        )

    def get_message_context(
        self,
        db: Session,
        current_user: User,
        server_id: uuid.UUID,
        channel_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        before: int = 20,
        after: int = 20,
    ) -> ServerChannelMessageContextResponse:
        channel = self._require_channel_access(db, current_user, server_id, channel_id)
        target = ServerChannelMessageRepository.get_by_id(db, message_id)
        if target is None or target.channel_id != channel.id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Channel message not found: {message_id}",
            )
        root_target = target
        if target.thread_root_message_id is not None:
            root = ServerChannelMessageRepository.get_by_id(
                db,
                target.thread_root_message_id,
            )
            if root is not None and root.channel_id == channel.id:
                root_target = root
        before_messages = ServerChannelMessageRepository.list_from_anchor(
            db,
            channel.id,
            anchor_message=root_target,
            direction="before",
            limit=max(0, min(before, 100)),
        )
        after_messages = ServerChannelMessageRepository.list_from_anchor(
            db,
            channel.id,
            anchor_message=root_target,
            direction="after",
            limit=max(0, min(after, 100)),
        )
        messages = [*reversed(before_messages), root_target, *after_messages]
        if target.thread_root_message_id is not None and target.id != root_target.id:
            messages.append(target)
        message_by_id = {item.id: item for item in messages}
        messages = sorted(
            message_by_id.values(),
            key=lambda item: (item.created_at, item.id),
        )
        author_profiles = list_user_public_profiles_by_id(
            db,
            [
                item.author_user_id
                for item in messages
                if item.author_user_id is not None
            ],
        )
        reply_counts = ServerChannelMessageRepository.count_replies_by_roots(
            db,
            [item.id for item in messages],
        )
        from app.services.server_channel_message_reaction_service import (
            ServerChannelMessageReactionService,
        )

        reactions = ServerChannelMessageReactionService().list_grouped_by_messages(
            db,
            [item.id for item in messages],
            current_user_id=current_user.id,
        )
        author_agents = self._load_author_agents(db, server_id, messages)
        responses = [
            self._build_message_response(
                item,
                reply_count=reply_counts.get(item.id, 0),
                author_user=author_profiles.get(item.author_user_id or ""),
                author_agent=author_agents.get(item.id),
                reactions=reactions.get(item.id, []),
            )
            for item in messages
        ]
        target_response = next(
            (item for item in responses if item.message_id == target.id),
            self._build_message_response(target),
        )
        return ServerChannelMessageContextResponse(
            target=target_response,
            messages=responses,
        )
