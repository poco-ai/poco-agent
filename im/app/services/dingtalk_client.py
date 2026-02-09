import logging

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class DingTalkClient:
    provider = "dingtalk"
    max_text_length = 1800

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.dingtalk_enabled)
        self._fallback_webhook = (settings.dingtalk_webhook_url or "").strip()

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send_text(self, *, destination: str, text: str) -> None:
        if not self._enabled:
            return

        url = destination if destination.startswith("http") else self._fallback_webhook
        if not url:
            logger.warning(
                "dingtalk_send_skipped",
                extra={"reason": "no_webhook_url", "destination": destination},
            )
            return

        payload = {
            "msgtype": "text",
            "text": {"content": text},
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, json=payload)
        if not resp.is_success:
            logger.warning(
                "dingtalk_send_failed",
                extra={"status_code": resp.status_code, "response": resp.text[:300]},
            )
