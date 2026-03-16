import asyncio
import importlib
import inspect
import json
import logging
import threading
from concurrent.futures import Future
from typing import Any
from urllib.parse import quote_plus

import dingtalk_stream
import websockets

from app.core.settings import get_settings
from app.schemas.im import InboundMessage
from app.services.im import InboundMessageService
from app.services.im_providers import (
    clean_dingtalk_text,
    dingtalk_has_explicit_mention,
    parse_feishu_stream_event,
)

logger = logging.getLogger(__name__)

try:
    import lark_oapi as lark
    import lark_oapi.ws as lark_ws
except ImportError:
    lark = None
    lark_ws = None


class PocoDingTalkChatbotHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, *, inbound_service: InboundMessageService) -> None:
        super().__init__()
        self._inbound_service = inbound_service

    async def process(  # type: ignore[override]
        self,
        message: dingtalk_stream.CallbackMessage,
    ) -> tuple[int, str]:
        try:
            incoming = dingtalk_stream.ChatbotMessage.from_dict(message.data)
        except Exception:
            logger.exception("dingtalk_stream_parse_message_failed")
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        msg_type = str(incoming.message_type or "").strip().lower()
        if msg_type and msg_type != "text":
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        raw_text = ""
        if incoming.text and isinstance(incoming.text.content, str):
            raw_text = incoming.text.content.strip()

        sender_uid = str(incoming.sender_id or incoming.sender_staff_id or "").strip()
        bot_uid = str(incoming.chatbot_user_id or "").strip()
        if sender_uid and bot_uid and sender_uid == bot_uid:
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        if not dingtalk_has_explicit_mention(
            conversation_type=str(incoming.conversation_type or "").strip(),
            is_in_at_list=incoming.is_in_at_list,
            at_users=incoming.at_users,
            bot_user_id=bot_uid or None,
            raw_text=raw_text,
        ):
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        text = clean_dingtalk_text(raw_text)
        if not text:
            text = "/help"

        conversation_id = str(incoming.conversation_id or "").strip()
        if not conversation_id:
            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        session_webhook = str(incoming.session_webhook or "").strip() or None
        message_id = str(incoming.message_id or message.headers.message_id or "").strip()
        sender_id = (
            str(incoming.sender_staff_id or incoming.sender_id or incoming.sender_nick or "").strip()
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
        self,
        message: dingtalk_stream.CallbackMessage,
    ) -> tuple[int, str]:
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
        self,
        event: dingtalk_stream.EventMessage,
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
        self._client_id = (settings.dingtalk_client_id or "").strip()
        self._client_secret = (settings.dingtalk_client_secret or "").strip()
        self._subscribe_events = bool(settings.dingtalk_stream_subscribe_events)
        self._inbound_service = InboundMessageService()
        self._client: dingtalk_stream.DingTalkStreamClient | None = None

        if self._enabled and self._client_id and self._client_secret:
            credential = dingtalk_stream.Credential(
                self._client_id,
                self._client_secret,
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
                    "dingtalk_stream_connection_closed",
                    extra={"error": str(exc)},
                )
                await asyncio.sleep(10)
            except Exception:
                logger.exception("dingtalk_stream_loop_failed")
                await asyncio.sleep(3)


def _get_lark_sdk() -> Any:
    if lark is None:
        raise RuntimeError("lark_oapi is not installed")
    return lark


def _get_lark_ws_sdk() -> Any:
    if lark_ws is None:
        raise RuntimeError("lark_oapi.ws is not installed")
    return lark_ws


class FeishuStreamService:
    _reconnect_delay_seconds = 3.0

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.feishu_enabled and settings.feishu_stream_enabled)
        self._app_id = (settings.feishu_app_id or "").strip()
        self._app_secret = (settings.feishu_app_secret or "").strip()
        self._base_url = (settings.feishu_base_url or "").rstrip("/")
        self._inbound_service = InboundMessageService()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread_loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()
        self._client: Any = None

        if not self._enabled:
            return
        if not self._app_id or not self._app_secret:
            logger.warning("feishu_stream_disabled_missing_credentials")
            return
        if lark is None or lark_ws is None:
            logger.warning("feishu_stream_sdk_missing")
            return

    @property
    def enabled(self) -> bool:
        return bool(
            self._enabled
            and self._app_id
            and self._app_secret
            and lark is not None
            and lark_ws is not None
        )

    async def run_forever(self) -> None:
        if not self.enabled:
            return

        lark_sdk = _get_lark_sdk()
        lark_ws_sdk = _get_lark_ws_sdk()
        self._loop = asyncio.get_running_loop()
        self._stopping.clear()

        try:
            while not self._stopping.is_set():
                finished = asyncio.Event()
                thread = threading.Thread(
                    target=self._build_runner(
                        finished=finished,
                        lark_sdk=lark_sdk,
                        lark_ws_sdk=lark_ws_sdk,
                    ),
                    name="feishu-stream",
                    daemon=True,
                )
                self._thread = thread
                thread.start()
                await finished.wait()
                self._thread = None

                if self._stopping.is_set():
                    break

                logger.warning(
                    "feishu_stream_disconnected_restarting",
                    extra={"delay_seconds": self._reconnect_delay_seconds},
                )
                await asyncio.sleep(self._reconnect_delay_seconds)
        except asyncio.CancelledError:
            await self._stop_client()
            raise
        finally:
            self._thread = None

    def _build_runner(
        self,
        *,
        finished: asyncio.Event,
        lark_sdk: Any,
        lark_ws_sdk: Any,
    ):
        def _runner() -> None:
            thread_loop: asyncio.AbstractEventLoop | None = None
            try:
                thread_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(thread_loop)
                self._thread_loop = thread_loop

                client_module = importlib.import_module("lark_oapi.ws.client")
                setattr(client_module, "loop", thread_loop)

                event_handler = (
                    lark_sdk.EventDispatcherHandler.builder("", "")
                    .register_p2_im_message_receive_v1(self._handle_message_event)
                    .build()
                )
                self._client = lark_ws_sdk.Client(
                    self._app_id,
                    self._app_secret,
                    event_handler=event_handler,
                    domain=self._base_url or "https://open.feishu.cn",
                )
                logger.info("feishu_stream_starting")
                self._client.start()
            except Exception:
                if self._stopping.is_set():
                    logger.info("feishu_stream_stopped")
                else:
                    logger.exception("feishu_stream_loop_failed")
            finally:
                self._client = None
                self._thread_loop = None
                if thread_loop is not None and not thread_loop.is_closed():
                    try:
                        thread_loop.close()
                    except Exception:
                        logger.exception("feishu_stream_loop_close_failed")
                if self._loop is not None:
                    try:
                        self._loop.call_soon_threadsafe(finished.set)
                    except RuntimeError:
                        pass

        return _runner

    def _handle_message_event(self, data: Any) -> None:
        inbound = parse_feishu_stream_event(data)
        if inbound is None:
            return

        loop = self._loop
        if loop is None:
            logger.warning("feishu_stream_loop_unavailable")
            return

        future = asyncio.run_coroutine_threadsafe(
            self._inbound_service.handle_message(message=inbound),
            loop,
        )
        future.add_done_callback(lambda fut: _log_future_exception(fut, inbound=inbound))

    async def _stop_client(self) -> None:
        thread_loop = self._thread_loop
        thread = self._thread
        if thread_loop is None:
            return

        self._stopping.set()

        async def _shutdown() -> None:
            client = self._client
            try:
                if client is not None:
                    disconnect = getattr(client, "_disconnect", None)
                    if callable(disconnect):
                        result = disconnect()
                        if inspect.isawaitable(result):
                            await result
            except Exception:
                logger.exception("feishu_stream_stop_failed")
            finally:
                asyncio.get_running_loop().stop()

        def _schedule_shutdown() -> None:
            asyncio.create_task(_shutdown())

        try:
            thread_loop.call_soon_threadsafe(_schedule_shutdown)
        except RuntimeError:
            pass

        if thread is not None and thread.is_alive():
            await asyncio.to_thread(thread.join, 5)


def _log_future_exception(future: Future[None], *, inbound: InboundMessage) -> None:
    try:
        future.result()
    except Exception:
        logger.exception(
            "feishu_stream_handle_message_failed",
            extra={
                "provider": inbound.provider,
                "destination": inbound.destination,
                "message_id": inbound.message_id,
            },
        )
