import logging

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramClient:
    provider = "telegram"
    max_text_length = 3500

    def __init__(self) -> None:
        settings = get_settings()
        token = (settings.telegram_bot_token or "").strip()
        self._enabled = bool(token)
        self._base_url = f"https://api.telegram.org/bot{token}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send_text(self, *, destination: str, text: str) -> None:
        if not self._enabled:
            return
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": destination,
            "text": text,
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, json=payload)
        if not resp.is_success:
            logger.warning(
                "telegram_send_failed",
                extra={"status_code": resp.status_code, "response": resp.text[:300]},
            )
