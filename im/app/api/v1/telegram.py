import logging
from typing import Any

from fastapi import APIRouter, Header, Request

from app.core.settings import get_settings
from app.schemas.im_message import InboundMessage
from app.schemas.response import Response
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])


@router.post("")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    settings = get_settings()
    if settings.telegram_webhook_secret_token:
        if (
            not x_telegram_bot_api_secret_token
            or x_telegram_bot_api_secret_token != settings.telegram_webhook_secret_token
        ):
            return Response.error(
                code=403, message="Invalid webhook token", status_code=403
            )

    payload = await request.json()
    inbound = _parse_telegram_update(payload)
    if inbound is None:
        return Response.success(data={"ok": True, "ignored": True})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return Response.success(data={"ok": True})


def _parse_telegram_update(payload: dict[str, Any]) -> InboundMessage | None:
    message = payload.get("message") or payload.get("edited_message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None

    chat_id = chat.get("id")
    if chat_id is None:
        return None

    text = message.get("text")
    if not isinstance(text, str):
        return None

    raw_message_id = message.get("message_id")
    update_id = payload.get("update_id")
    message_id = str(raw_message_id or update_id or "")

    sender_id = None
    sender = message.get("from")
    if isinstance(sender, dict):
        raw_sender_id = sender.get("id")
        if raw_sender_id is not None:
            sender_id = str(raw_sender_id)

    return InboundMessage(
        provider="telegram",
        destination=str(chat_id),
        message_id=message_id,
        sender_id=sender_id,
        text=text,
        raw=payload,
    )
