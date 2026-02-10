import asyncio
import json
import logging
from urllib.parse import quote_plus

import websockets

import dingtalk_stream

from app.core.settings import get_settings
from app.schemas.im_message import InboundMessage
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)


def _is_truthy(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _clean_text(text: str) -> str:
    cleaned = (text or "").replace("\u2005", " ").replace("\u2006", " ").strip()
    # DingTalk may prepend "@BotName" to the message content in group chats.
    # Strip leading mentions so command parsing works (e.g. "/list", "/new ...").
    while cleaned.startswith(("@", "＠")):
        parts = cleaned.split(maxsplit=1)
        if len(parts) == 1:
            return ""
        cleaned = parts[1].strip()
    return cleaned


class PocoDingTalkChatbotHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, *, inbound_service: InboundMessageService) -> None:
        super().__init__()
        self._inbound_service = inbound_service

    async def process(  # type: ignore[override]
        self, message: dingtalk_stream.CallbackMessage
    ) -> tuple[int, str]:
        try:
            incoming = dingtalk_stream.ChatbotMessage.from_dict(message.data)
        except Exception:
            logger.exception("dingtalk_stream_parse_message_failed")
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        msg_type = str(incoming.message_type or "").strip().lower()
        if msg_type and msg_type != "text":
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        conversation_type = str(incoming.conversation_type or "").strip()
        if conversation_type == "2" and incoming.is_in_at_list is not None:
            if not _is_truthy(incoming.is_in_at_list):
                return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        # Ignore bot self messages to avoid loops.
        sender_uid = str(incoming.sender_id or incoming.sender_staff_id or "").strip()
        bot_uid = str(incoming.chatbot_user_id or "").strip()
        if sender_uid and bot_uid and sender_uid == bot_uid:
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        raw_text = ""
        if incoming.text and isinstance(incoming.text.content, str):
            raw_text = incoming.text.content.strip()
        text = _clean_text(raw_text)
        if not text:
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        conversation_id = str(incoming.conversation_id or "").strip()
        if not conversation_id:
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        # sessionWebhook is still useful for immediate replies, but can expire.
        session_webhook = str(incoming.session_webhook or "").strip() or None
        message_id = str(
            incoming.message_id or message.headers.message_id or ""
        ).strip()
        sender_id = (
            str(
                incoming.sender_staff_id
                or incoming.sender_id
                or incoming.sender_nick
                or ""
            ).strip()
            or None
        )

        inbound = InboundMessage(
            provider="dingtalk",
            destination=conversation_id,
            send_address=session_webhook,
            message_id=message_id,
            sender_id=sender_id,
            text=text,
            raw=message.data if isinstance(message.data, dict) else None,
        )
        await self._inbound_service.handle_message(message=inbound)
        return dingtalk_stream.AckMessage.STATUS_OK, "OK"


class PocoDingTalkCardCallbackHandler(dingtalk_stream.CallbackHandler):
    async def process(  # type: ignore[override]
        self, message: dingtalk_stream.CallbackMessage
    ) -> tuple[int, str]:
        # Note: Card callback payload values are often JSON strings; parsing is best-effort.
        try:
            msg = dingtalk_stream.CardCallbackMessage.from_dict(message.data)
            logger.info(
                "dingtalk_card_callback",
                extra={
                    "corp_id": msg.corp_id,
                    "user_id": msg.user_id,
                    "card_instance_id": msg.card_instance_id,
                    "content": msg.content,
                    "extension": msg.extension,
                },
            )
        except Exception:
            logger.exception("dingtalk_card_callback_parse_failed")
        return dingtalk_stream.AckMessage.STATUS_OK, "OK"


class PocoDingTalkEventHandler(dingtalk_stream.EventHandler):
    async def process(  # type: ignore[override]
        self, event: dingtalk_stream.EventMessage
    ) -> tuple[int, str]:
        logger.info(
            "dingtalk_event",
            extra={
                "topic": event.headers.topic,
                "event_type": event.headers.event_type,
                "event_id": event.headers.event_id,
            },
        )
        return dingtalk_stream.AckMessage.STATUS_OK, "OK"


class DingTalkStreamService:
    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(
            settings.dingtalk_enabled and settings.dingtalk_stream_enabled
        )
        self._client_id = (settings.dingtalk_app_key or "").strip()
        self._client_secret = (settings.dingtalk_app_secret or "").strip()
        self._subscribe_events = bool(settings.dingtalk_stream_subscribe_events)

        self._inbound_service = InboundMessageService()

        self._client: dingtalk_stream.DingTalkStreamClient | None = None
        if self._enabled and self._client_id and self._client_secret:
            credential = dingtalk_stream.Credential(
                self._client_id, self._client_secret
            )
            self._client = dingtalk_stream.DingTalkStreamClient(credential)
            self._client.register_callback_handler(
                dingtalk_stream.ChatbotMessage.TOPIC,
                PocoDingTalkChatbotHandler(inbound_service=self._inbound_service),
            )
            self._client.register_callback_handler(
                dingtalk_stream.Card_Callback_Router_Topic,
                PocoDingTalkCardCallbackHandler(),
            )
            if self._subscribe_events:
                self._client.register_all_event_handler(PocoDingTalkEventHandler())

    @property
    def enabled(self) -> bool:
        return bool(self._client)

    async def run_forever(self) -> None:
        client = self._client
        if client is None:
            return
        client.pre_start()

        while True:
            try:
                connection = await asyncio.to_thread(client.open_connection)
                if not connection:
                    await asyncio.sleep(10)
                    continue

                endpoint = str(connection.get("endpoint") or "").strip()
                ticket = str(connection.get("ticket") or "").strip()
                if not endpoint or not ticket:
                    await asyncio.sleep(10)
                    continue

                uri = f"{endpoint}?ticket={quote_plus(ticket)}"
                async with websockets.connect(uri) as websocket:
                    client.websocket = websocket
                    keepalive_task = asyncio.create_task(client.keepalive(websocket))
                    try:
                        async for raw_message in websocket:
                            json_message = json.loads(raw_message)
                            asyncio.create_task(client.background_task(json_message))
                    finally:
                        keepalive_task.cancel()
                        await asyncio.gather(keepalive_task, return_exceptions=True)
            except asyncio.CancelledError:
                ws = getattr(client, "websocket", None)
                if ws:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                raise
            except websockets.exceptions.ConnectionClosedError as exc:
                logger.warning(
                    "dingtalk_stream_connection_closed", extra={"error": str(exc)}
                )
                await asyncio.sleep(10)
                continue
            except Exception:
                logger.exception("dingtalk_stream_loop_failed")
                await asyncio.sleep(3)
                continue
