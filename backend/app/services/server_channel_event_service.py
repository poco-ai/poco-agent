import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.server_channel_message import ServerChannelMessage
from app.repositories.server_channel_message_repository import (
    ServerChannelMessageRepository,
)


@dataclass(slots=True)
class ChannelEventActor:
    actor_type: str
    actor_label: str
    actor_user_id: str | None = None
    actor_agent_identity_id: uuid.UUID | None = None
    actor_agent_handle: str | None = None
    actor_session_id: uuid.UUID | None = None


@dataclass(slots=True)
class ChannelEventTarget:
    target_label: str
    target_user_id: str | None = None
    target_agent_identity_id: uuid.UUID | None = None
    target_agent_handle: str | None = None


def create_channel_event_message(
    db: Session,
    *,
    channel_id: uuid.UUID,
    event_type: str,
    actor: ChannelEventActor,
    target: ChannelEventTarget | None,
    content: dict[str, object],
    text_preview: str,
    thread_root_message_id: uuid.UUID | None = None,
) -> ServerChannelMessage:
    event_content: dict[str, object] = {
        "event_type": event_type,
        "actor_type": actor.actor_type,
        "actor_label": actor.actor_label,
        "actor_user_id": actor.actor_user_id,
        "actor_agent_identity_id": str(actor.actor_agent_identity_id)
        if actor.actor_agent_identity_id is not None
        else None,
        "actor_agent_handle": actor.actor_agent_handle,
        "actor_session_id": str(actor.actor_session_id)
        if actor.actor_session_id is not None
        else None,
    }
    if target is not None:
        event_content.update(
            {
                "target_label": target.target_label,
                "target_user_id": target.target_user_id,
                "target_agent_identity_id": str(target.target_agent_identity_id)
                if target.target_agent_identity_id is not None
                else None,
                "target_agent_handle": target.target_agent_handle,
            }
        )
    event_content.update(content)

    message = ServerChannelMessageRepository.create(
        db,
        ServerChannelMessage(
            channel_id=channel_id,
            author_user_id=None,
            message_type="event",
            content=event_content,
            text_preview=text_preview,
            thread_root_message_id=thread_root_message_id,
        ),
    )
    db.flush()
    return message
