import logging

from app.services.dingtalk_client import DingTalkClient
from app.services.feishu_client import FeishuClient
from app.services.provider_protocol import MessageProvider
from app.services.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class NotificationGateway:
    def __init__(self) -> None:
        self._providers: dict[str, MessageProvider] = {
            "telegram": TelegramClient(),
            "dingtalk": DingTalkClient(),
            "feishu": FeishuClient(),
        }

    def get_provider(self, provider: str) -> MessageProvider | None:
        return self._providers.get(provider)

    async def send_text(self, *, provider: str, destination: str, text: str) -> bool:
        client = self.get_provider(provider)
        if not client:
            logger.warning("unknown_im_provider", extra={"provider": provider})
            return True
        if not client.enabled:
            logger.warning(
                "im_provider_disabled",
                extra={"provider": provider},
            )
            return True

        chunks = _split_text(text, max(1, client.max_text_length))
        all_sent = True
        for chunk in chunks:
            sent = await client.send_text(destination=destination, text=chunk)
            all_sent = all_sent and sent
            if not sent:
                break
        return all_sent


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks
