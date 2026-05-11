import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.server_channel import ServerChannel
from app.repositories.server_channel_repository import (
    ServerChannelMemberRepository,
    ServerChannelRepository,
)
from app.services.server_member_service import require_server_member


def require_channel_member_access(
    db: Session,
    *,
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    user_id: str,
) -> ServerChannel:
    require_server_member(db, server_id, user_id)
    channel = ServerChannelRepository.get_by_id(db, channel_id)
    if channel is None or channel.server_id != server_id:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Channel not found: {channel_id}",
        )

    membership = ServerChannelMemberRepository.get_by_channel_and_user(
        db,
        channel.id,
        user_id,
    )
    if membership is None or membership.status != "active":
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Channel membership is required",
        )
    return channel
