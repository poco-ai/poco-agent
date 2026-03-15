import asyncio
import importlib
import inspect
import logging
import threading
from concurrent.futures import Future
from typing import Any

from app.core.settings import get_settings
from app.schemas.im_message import InboundMessage
from app.services.feishu_event_parser import parse_feishu_stream_event
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)

try:
    import lark_oapi as lark
    import lark_oapi.ws as lark_ws
except ImportError:
    lark = None
    lark_ws = None


def _get_lark_sdk() -> Any:
    if lark is None:
        raise RuntimeError("lark_oapi is not installed")
    return lark


def _get_lark_ws_sdk() -> Any:
    if lark_ws is None:
        raise RuntimeError("lark_oapi.ws is not installed")
    return lark_ws


class FeishuStreamService:
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
        finished = asyncio.Event()
        self._stopping.clear()

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

        thread = threading.Thread(
            target=_runner,
            name="feishu-stream",
            daemon=True,
        )
        self._thread = thread
        thread.start()

        try:
            await finished.wait()
        except asyncio.CancelledError:
            await self._stop_client()
            raise
        finally:
            self._thread = None

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
        future.add_done_callback(
            lambda fut: _log_future_exception(fut, inbound=inbound)
        )

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


def _log_future_exception(
    future: Future[None],
    *,
    inbound: InboundMessage,
) -> None:
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
