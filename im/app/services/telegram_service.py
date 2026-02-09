import logging
from typing import Any


from app.core.database import SessionLocal
from app.repositories.channel_repository import ChannelRepository
from app.services.command_service import CommandService
from app.services.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class TelegramService:
    """Handle Telegram webhook updates and route commands."""

    def __init__(self) -> None:
        self.client = TelegramClient()
        self.commands = CommandService()

    async def handle_update(self, payload: dict[str, Any]) -> None:
        if not self.client.enabled:
            return

        message = payload.get("message") or payload.get("edited_message")
        if not isinstance(message, dict):
            return

        chat = message.get("chat")
        if not isinstance(chat, dict):
            return

        chat_id = chat.get("id")
        if chat_id is None:
            return

        text = message.get("text")
        if not isinstance(text, str):
            return

        db = SessionLocal()
        try:
            channel = ChannelRepository.get_or_create(
                db,
                provider="telegram",
                destination=str(chat_id),
            )
            responses = await self.commands.handle_text(
                db=db, channel=channel, text=text
            )
        finally:
            db.close()

        for resp in responses:
            await self.client.send_text(destination=str(chat_id), text=resp)
