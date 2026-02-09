from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.channel import Channel
from app.repositories.channel_delivery_repository import ChannelDeliveryRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.dedup_repository import DedupRepository
from app.schemas.im_message import InboundMessage
from app.services.command_service import CommandService
from app.services.notification_gateway import NotificationGateway


class InboundMessageService:
    def __init__(self) -> None:
        self.commands = CommandService()
        self.gateway = NotificationGateway()

    async def handle_message(self, *, message: InboundMessage) -> None:
        db = SessionLocal()
        responses: list[str] = []
        send_address: str | None = None
        try:
            if message.message_id:
                dedup_key = f"in:{message.provider}:{message.message_id}"
                if not DedupRepository.put_if_absent(db, key=dedup_key):
                    return

            channel = ChannelRepository.get_or_create(
                db,
                provider=message.provider,
                destination=message.destination,
            )
            send_address = _resolve_send_address(
                db,
                channel=channel,
                message=message,
            )
            responses = await self.commands.handle_text(
                db=db,
                channel=channel,
                text=message.text,
            )
        finally:
            db.close()

        if not responses:
            return

        target = send_address or message.destination
        for resp in responses:
            await self.gateway.send_text(
                provider=message.provider,
                destination=target,
                text=resp,
            )


def _resolve_send_address(
    db: Session,
    *,
    channel: Channel,
    message: InboundMessage,
) -> str:
    candidate = (message.send_address or "").strip()
    if candidate:
        ChannelDeliveryRepository.upsert_send_address(
            db,
            channel_id=channel.id,
            send_address=candidate,
        )
        return candidate

    stored = ChannelDeliveryRepository.get_send_address(db, channel_id=channel.id)
    return (stored or "").strip() or channel.destination
