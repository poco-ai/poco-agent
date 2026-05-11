import uuid

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.models.server_channel import ServerChannel
from app.models.server_channel_member import ServerChannelMember


class ServerChannelRepository:
    @staticmethod
    def create(session_db: Session, channel: ServerChannel) -> ServerChannel:
        session_db.add(channel)
        return channel

    @staticmethod
    def get_by_id(
        session_db: Session,
        channel_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> ServerChannel | None:
        query = session_db.query(ServerChannel).filter(ServerChannel.id == channel_id)
        if not include_archived:
            query = query.filter(ServerChannel.archived_at.is_(None))
        return query.first()

    @staticmethod
    def get_by_server_slug(
        session_db: Session,
        server_id: uuid.UUID,
        slug: str,
        *,
        exclude_channel_id: uuid.UUID | None = None,
    ) -> ServerChannel | None:
        query = session_db.query(ServerChannel).filter(
            ServerChannel.server_id == server_id,
            ServerChannel.slug == slug,
            ServerChannel.archived_at.is_(None),
        )
        if exclude_channel_id is not None:
            query = query.filter(ServerChannel.id != exclude_channel_id)
        return query.first()

    @staticmethod
    def list_by_server_for_user(
        session_db: Session,
        server_id: uuid.UUID,
        user_id: str,
    ) -> list[ServerChannel]:
        return (
            session_db.query(ServerChannel)
            .join(
                ServerChannelMember,
                (ServerChannelMember.channel_id == ServerChannel.id)
                & (ServerChannelMember.user_id == user_id)
                & (ServerChannelMember.status == "active"),
            )
            .filter(
                ServerChannel.server_id == server_id,
                ServerChannel.archived_at.is_(None),
            )
            .order_by(ServerChannel.created_at.asc(), ServerChannel.name.asc())
            .all()
        )

    @staticmethod
    def get_system_channel(
        session_db: Session,
        server_id: uuid.UUID,
        system_channel_type: str,
    ) -> ServerChannel | None:
        return (
            session_db.query(ServerChannel)
            .filter(
                ServerChannel.server_id == server_id,
                ServerChannel.system_channel_type == system_channel_type,
                ServerChannel.archived_at.is_(None),
            )
            .first()
        )

    @staticmethod
    def list_default_public_candidates(
        session_db: Session,
        server_id: uuid.UUID,
    ) -> list[ServerChannel]:
        slug_priority = case(
            (ServerChannel.slug == "public", 0),
            (ServerChannel.slug == "general", 1),
            else_=2,
        )
        return (
            session_db.query(ServerChannel)
            .filter(
                ServerChannel.server_id == server_id,
                ServerChannel.conversation_type == "channel",
                ServerChannel.visibility == "public",
                ServerChannel.archived_at.is_(None),
            )
            .order_by(slug_priority.asc(), ServerChannel.created_at.asc())
            .all()
        )

    @staticmethod
    def get_direct_message(
        session_db: Session,
        *,
        server_id: uuid.UUID,
        direct_user_id: str | None,
        direct_agent_identity_id: uuid.UUID | None,
    ) -> ServerChannel | None:
        query = session_db.query(ServerChannel).filter(
            ServerChannel.server_id == server_id,
            ServerChannel.conversation_type == "direct_message",
            ServerChannel.archived_at.is_(None),
        )
        if direct_user_id is not None:
            query = query.filter(ServerChannel.direct_user_id == direct_user_id)
        else:
            query = query.filter(ServerChannel.direct_user_id.is_(None))
        if direct_agent_identity_id is not None:
            query = query.filter(
                ServerChannel.direct_agent_identity_id == direct_agent_identity_id
            )
        else:
            query = query.filter(ServerChannel.direct_agent_identity_id.is_(None))
        return query.first()

    @staticmethod
    def delete(session_db: Session, channel: ServerChannel) -> None:
        session_db.delete(channel)


class ServerChannelMemberRepository:
    @staticmethod
    def create(
        session_db: Session,
        membership: ServerChannelMember,
    ) -> ServerChannelMember:
        session_db.add(membership)
        return membership

    @staticmethod
    def get_by_channel_and_user(
        session_db: Session,
        channel_id: uuid.UUID,
        user_id: str,
    ) -> ServerChannelMember | None:
        return (
            session_db.query(ServerChannelMember)
            .filter(
                ServerChannelMember.channel_id == channel_id,
                ServerChannelMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def list_by_channel(
        session_db: Session,
        channel_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[ServerChannelMember]:
        query = session_db.query(ServerChannelMember).filter(
            ServerChannelMember.channel_id == channel_id,
        )
        if active_only:
            query = query.filter(ServerChannelMember.status == "active")
        return query.order_by(
            ServerChannelMember.joined_at.asc(),
            ServerChannelMember.id.asc(),
        ).all()

    @staticmethod
    def get_by_id(
        session_db: Session,
        membership_id: int,
    ) -> ServerChannelMember | None:
        return (
            session_db.query(ServerChannelMember)
            .filter(ServerChannelMember.id == membership_id)
            .first()
        )

    @staticmethod
    def delete(session_db: Session, membership: ServerChannelMember) -> None:
        session_db.delete(membership)
