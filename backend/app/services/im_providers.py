import asyncio
import json
import logging
import re
import time
from typing import Any, Protocol

import httpx

from app.core.settings import get_settings
from app.schemas.im import InboundMessage

logger = logging.getLogger(__name__)

_DINGTALK_LEADING_MENTION_RE = re.compile(r"^(?:[@\uff20][^\s]+\s*)+")
_FEISHU_LEADING_MENTION_RE = re.compile(r"^(?:<at\s+[^>]*>.*?</at>\s*)+", re.IGNORECASE)
_FEISHU_AT_TAG_RE = re.compile(r"<at\s+([^>]*?)>(.*?)</at>", re.IGNORECASE | re.DOTALL)
_FEISHU_AT_ID_ATTR_RE = re.compile(
    r"(?:user_id|open_id|union_id|id)\s*=\s*[\"']?([^\"'\s>]+)",
    re.IGNORECASE,
)


class MessageProvider(Protocol):
    provider: str
    max_text_length: int

    @property
    def enabled(self) -> bool: ...

    async def send_text(self, *, destination: str, text: str) -> bool: ...


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

    async def send_text(self, *, destination: str, text: str) -> bool:
        if not self._enabled:
            return False
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
            return False
        return True


class DingTalkClient:
    provider = "dingtalk"
    max_text_length = 1800

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.dingtalk_enabled)
        self._fallback_webhook = (settings.dingtalk_webhook_url or "").strip()
        self._open_base_url = (settings.dingtalk_open_base_url or "").rstrip("/")
        self._client_id = (settings.dingtalk_client_id or "").strip()
        self._client_secret = (settings.dingtalk_client_secret or "").strip()
        self._robot_code = (settings.dingtalk_robot_code or "").strip()
        self._openapi_enabled = bool(
            self._open_base_url
            and self._client_id
            and self._client_secret
            and self._robot_code
        )
        self._token_lock = asyncio.Lock()
        self._access_token: str | None = None
        self._token_expire_ts = 0.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _refresh_access_token(self) -> None:
        if not self._openapi_enabled:
            raise RuntimeError("DingTalk OpenAPI is not configured")

        url = f"{self._open_base_url}/v1.0/oauth2/accessToken"
        payload = {
            "appKey": self._client_id,
            "appSecret": self._client_secret,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, json=payload)
        if not resp.is_success:
            raise RuntimeError(f"DingTalk auth failed: HTTP {resp.status_code}")

        data = resp.json()
        token = data.get("accessToken") or data.get("access_token")
        expire = data.get("expireIn") or data.get("expires_in")
        if not token:
            raise RuntimeError(
                f"DingTalk auth failed: missing access token, response={str(data)[:300]}"
            )

        ttl = int(expire) if isinstance(expire, int) and expire > 0 else 7200
        self._access_token = str(token)
        self._token_expire_ts = time.time() + max(120, ttl - 60)

    async def _get_access_token(self) -> str:
        if (
            self._access_token
            and self._token_expire_ts > 0
            and self._token_expire_ts > time.time()
        ):
            return self._access_token

        async with self._token_lock:
            if (
                self._access_token
                and self._token_expire_ts > 0
                and self._token_expire_ts > time.time()
            ):
                return self._access_token
            await self._refresh_access_token()
            if not self._access_token:
                raise RuntimeError("DingTalk token is empty")
            return self._access_token

    async def _send_via_webhook(self, *, url: str, text: str) -> bool:
        payload = {
            "msgtype": "text",
            "text": {"content": text},
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, json=payload)
        if resp.is_success:
            return True

        logger.warning(
            "dingtalk_send_failed",
            extra={"status_code": resp.status_code, "response": resp.text[:300]},
        )
        return False

    async def _send_via_openapi(self, *, conversation_id: str, text: str) -> bool:
        if not self._openapi_enabled:
            return False

        try:
            token = await self._get_access_token()
        except Exception:
            logger.exception("dingtalk_auth_error")
            return False

        headers = {"x-acs-dingtalk-access-token": token}
        msg_param = json.dumps({"content": text}, ensure_ascii=False)
        payload = {
            "openConversationId": conversation_id,
            "robotCode": self._robot_code,
            "msgKey": "sampleText",
            "msgParam": msg_param,
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            group_url = f"{self._open_base_url}/v1.0/robot/groupMessages/send"
            resp = await client.post(group_url, json=payload, headers=headers)
            if resp.is_success:
                return True

            private_url = f"{self._open_base_url}/v1.0/robot/privateChatMessages/send"
            resp2 = await client.post(private_url, json=payload, headers=headers)
            if resp2.is_success:
                return True

        logger.warning(
            "dingtalk_openapi_send_failed",
            extra={
                "conversation_id": conversation_id,
                "group_status_code": resp.status_code,
                "group_response": resp.text[:300],
                "private_status_code": resp2.status_code,
                "private_response": resp2.text[:300],
            },
        )
        return False

    async def send_text(self, *, destination: str, text: str) -> bool:
        if not self._enabled:
            return False

        dest = (destination or "").strip()
        if not dest:
            return False

        if dest.startswith("http"):
            return await self._send_via_webhook(url=dest, text=text)

        if await self._send_via_openapi(conversation_id=dest, text=text):
            return True

        if self._fallback_webhook:
            return await self._send_via_webhook(url=self._fallback_webhook, text=text)

        logger.warning(
            "dingtalk_send_skipped",
            extra={"reason": "no_route", "destination": dest},
        )
        return False


class FeishuClient:
    provider = "feishu"
    max_text_length = 3000

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings.feishu_enabled)
        self._base_url = (settings.feishu_base_url or "").rstrip("/")
        self._app_id = (settings.feishu_app_id or "").strip()
        self._app_secret = (settings.feishu_app_secret or "").strip()
        self._token_lock = asyncio.Lock()
        self._tenant_access_token: str | None = None
        self._token_expire_ts = 0.0

    @property
    def enabled(self) -> bool:
        return bool(
            self._enabled and self._base_url and self._app_id and self._app_secret
        )

    async def _refresh_tenant_access_token(self) -> None:
        if not self.enabled:
            raise RuntimeError("Feishu client is not configured")

        url = f"{self._base_url}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self._app_id,
            "app_secret": self._app_secret,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, json=payload)

        if not resp.is_success:
            raise RuntimeError(f"Feishu auth failed: HTTP {resp.status_code}")

        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError("Feishu auth failed: invalid JSON response")

        code = int(data.get("code") or 0)
        if code != 0:
            raise RuntimeError(f"Feishu auth failed: code={code} msg={data.get('msg')}")

        token = data.get("tenant_access_token")
        expire = data.get("expire") or data.get("expires_in")
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("Feishu auth failed: missing tenant_access_token")

        ttl = _parse_positive_int(expire, default=7200)
        self._tenant_access_token = token.strip()
        self._token_expire_ts = time.time() + max(120, ttl - 60)

    async def _get_tenant_access_token(self) -> str:
        if (
            self._tenant_access_token
            and self._token_expire_ts > 0
            and self._token_expire_ts > time.time()
        ):
            return self._tenant_access_token

        async with self._token_lock:
            if (
                self._tenant_access_token
                and self._token_expire_ts > 0
                and self._token_expire_ts > time.time()
            ):
                return self._tenant_access_token
            await self._refresh_tenant_access_token()
            if not self._tenant_access_token:
                raise RuntimeError("Feishu tenant access token is empty")
            return self._tenant_access_token

    async def _send_text_once(
        self,
        *,
        tenant_access_token: str,
        receive_id_type: str,
        receive_id: str,
        text: str,
    ) -> bool:
        url = f"{self._base_url}/open-apis/im/v1/messages"
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        headers = {"Authorization": f"Bearer {tenant_access_token}"}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(
                url,
                params={"receive_id_type": receive_id_type},
                json=payload,
                headers=headers,
            )

        if not resp.is_success:
            logger.warning(
                "feishu_send_failed",
                extra={
                    "receive_id_type": receive_id_type,
                    "status_code": resp.status_code,
                    "response": resp.text[:300],
                },
            )
            return False

        data = resp.json()
        if not isinstance(data, dict):
            logger.warning("feishu_send_failed_invalid_json")
            return False

        code = int(data.get("code") or 0)
        if code == 0:
            return True

        logger.warning(
            "feishu_send_failed",
            extra={
                "receive_id_type": receive_id_type,
                "code": code,
                "msg": data.get("msg"),
            },
        )
        return False

    async def send_text(self, *, destination: str, text: str) -> bool:
        if not self.enabled:
            return False

        receive_id_type, receive_id = _parse_receive_target(destination)
        if not receive_id:
            return False

        try:
            token = await self._get_tenant_access_token()
        except Exception:
            logger.exception("feishu_auth_error")
            return False

        if await self._send_text_once(
            tenant_access_token=token,
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            text=text,
        ):
            return True

        try:
            async with self._token_lock:
                self._tenant_access_token = None
                self._token_expire_ts = 0.0
            token = await self._get_tenant_access_token()
        except Exception:
            logger.exception("feishu_auth_error")
            return False

        return await self._send_text_once(
            tenant_access_token=token,
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            text=text,
        )


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
            return False
        if not client.enabled:
            logger.warning("im_provider_disabled", extra={"provider": provider})
            return False

        chunks = _split_text(text, max(1, client.max_text_length))
        all_sent = True
        for chunk in chunks:
            sent = await client.send_text(destination=destination, text=chunk)
            all_sent = all_sent and sent
            if not sent:
                break
        return all_sent


def parse_telegram_update(payload: dict[str, Any]) -> InboundMessage | None:
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


def parse_dingtalk_webhook_event(payload: dict[str, Any]) -> InboundMessage | None:
    msg_type = str(payload.get("msgtype") or payload.get("msgType") or "").strip()
    if msg_type and msg_type.lower() != "text":
        return None

    raw_text = _extract_dingtalk_text(payload)
    conversation_type = str(payload.get("conversationType") or "").strip()
    bot_user_id = str(payload.get("chatbotUserId") or "").strip() or None
    if not dingtalk_has_explicit_mention(
        conversation_type=conversation_type,
        is_in_at_list=payload.get("isInAtList"),
        at_users=payload.get("atUsers"),
        bot_user_id=bot_user_id,
        raw_text=raw_text,
    ):
        return None

    text = clean_dingtalk_text(raw_text)
    if not text:
        text = "/help"

    conversation_id = str(
        payload.get("openConversationId") or payload.get("conversationId") or ""
    ).strip()
    session_webhook = str(payload.get("sessionWebhook") or "").strip()
    destination = conversation_id or session_webhook
    if not destination:
        return None

    message_id = str(
        payload.get("msgId")
        or payload.get("messageId")
        or payload.get("createAt")
        or ""
    ).strip()
    raw_sender_uid = str(
        payload.get("senderStaffId") or payload.get("senderId") or ""
    ).strip()
    if raw_sender_uid and bot_user_id and raw_sender_uid == bot_user_id:
        return None

    sender_id = (
        str(
            payload.get("senderStaffId")
            or payload.get("senderId")
            or payload.get("senderNick")
            or ""
        ).strip()
        or None
    )

    return InboundMessage(
        provider="dingtalk",
        destination=destination,
        send_address=session_webhook or None,
        message_id=message_id,
        sender_id=sender_id,
        text=text,
        raw=payload,
    )


def clean_dingtalk_text(text: str) -> str:
    cleaned = _normalize_im_text(text)
    while True:
        matched = _DINGTALK_LEADING_MENTION_RE.match(cleaned)
        if not matched:
            break
        cleaned = cleaned[matched.end() :].strip()
    return cleaned


def dingtalk_has_explicit_mention(
    *,
    conversation_type: str,
    is_in_at_list: Any,
    at_users: Any,
    bot_user_id: str | None,
    raw_text: str,
) -> bool:
    if str(conversation_type or "").strip() != "2":
        return True

    if is_in_at_list is not None:
        return _is_truthy(is_in_at_list)

    if _dingtalk_at_users_include_bot(at_users=at_users, bot_user_id=bot_user_id):
        return True

    normalized = _normalize_im_text(raw_text)
    return bool(normalized and _DINGTALK_LEADING_MENTION_RE.match(normalized))


def parse_feishu_webhook_event(payload: dict[str, Any]) -> InboundMessage | None:
    return _build_feishu_inbound(
        header=payload.get("header"),
        event=payload.get("event"),
        raw=payload,
    )


def parse_feishu_stream_event(data: Any) -> InboundMessage | None:
    return _build_feishu_inbound(
        header=_read_field(data, "header"),
        event=_read_field(data, "event"),
        raw=_try_dump_dict(data),
    )


def _build_feishu_inbound(
    *,
    header: Any,
    event: Any,
    raw: dict[str, Any] | None,
) -> InboundMessage | None:
    if event is None:
        return None

    event_type = str(_read_field(header, "event_type") or "").strip()
    if event_type and event_type not in {
        "im.message.receive_v1",
        "p2.im.message.receive_v1",
    }:
        return None

    message = _read_field(event, "message")
    if message is None:
        return None

    message_type = str(_read_field(message, "message_type") or "").strip().lower()
    if message_type and message_type != "text":
        return None

    chat_id = str(_read_field(message, "chat_id") or "").strip()
    if not chat_id:
        return None

    sender = _read_field(event, "sender")
    sender_type = str(_read_field(sender, "sender_type") or "").strip().lower()
    if sender_type and sender_type != "user":
        return None

    raw_text = _extract_feishu_text(_read_field(message, "content"))
    chat_type = str(_read_field(message, "chat_type") or "").strip().lower()
    mentions = _read_field(message, "mentions")
    if chat_type != "p2p" and not _feishu_has_explicit_mention(
        raw_text=raw_text,
        mentions=mentions,
    ):
        return None

    text = _clean_feishu_text(raw_text)
    if not text:
        text = "/help"

    message_id = str(
        _read_field(message, "message_id") or _read_field(header, "event_id") or ""
    ).strip()

    return InboundMessage(
        provider="feishu",
        destination=chat_id,
        message_id=message_id,
        sender_id=_extract_feishu_sender_id(sender),
        text=text,
        raw=raw,
    )


def _extract_feishu_text(content: Any) -> str:
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return ""
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
        text = _read_field(parsed, "text")
        if isinstance(text, str):
            return text.strip()
        return stripped

    text = _read_field(content, "text")
    if isinstance(text, str):
        return text.strip()

    return ""


def _extract_feishu_sender_id(sender: Any) -> str | None:
    sender_id = _read_field(sender, "sender_id")
    for key in ("open_id", "user_id", "union_id"):
        value = _read_field(sender_id, key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for key in ("open_id", "user_id", "union_id"):
        value = _read_field(sender, key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _clean_feishu_text(text: str) -> str:
    cleaned = _normalize_im_text(text)
    while True:
        matched = _FEISHU_LEADING_MENTION_RE.match(cleaned)
        if not matched:
            break
        cleaned = cleaned[matched.end() :].strip()
    return cleaned


def _feishu_has_explicit_mention(*, raw_text: str, mentions: Any) -> bool:
    normalized = _normalize_im_text(raw_text)
    if not normalized:
        return False

    bot_ids, bot_names = _feishu_bot_identity_candidates()

    tag_mentions = _extract_feishu_leading_at_mentions(normalized)
    if tag_mentions:
        return _feishu_leading_mentions_include_bot(
            tag_mentions,
            mentions=mentions,
            bot_ids=bot_ids,
            bot_names=bot_names,
        )

    plain_mentions = _extract_feishu_leading_plain_mentions(normalized)
    if plain_mentions:
        return _feishu_leading_mentions_include_bot(
            plain_mentions,
            mentions=mentions,
            bot_ids=bot_ids,
            bot_names=bot_names,
        )

    return False


def _feishu_bot_identity_candidates() -> tuple[set[str], set[str]]:
    settings = get_settings()
    ids = {
        value.strip()
        for value in (
            settings.feishu_app_id,
            settings.feishu_bot_user_id,
            settings.feishu_bot_open_id,
            settings.feishu_bot_union_id,
        )
        if isinstance(value, str) and value.strip()
    }
    names = {
        (value or "").strip().casefold()
        for value in (settings.feishu_bot_name,)
        if isinstance(value, str) and value.strip()
    }
    return ids, names


def _extract_feishu_leading_at_mentions(text: str) -> list[dict[str, str]]:
    matched = _FEISHU_LEADING_MENTION_RE.match(text)
    if not matched:
        return []

    items: list[dict[str, str]] = []
    for tag_match in _FEISHU_AT_TAG_RE.finditer(matched.group(0)):
        attrs = tag_match.group(1) or ""
        display_name = re.sub(r"<[^>]+>", "", tag_match.group(2) or "").strip().casefold()
        candidate_ids = {
            attr_match.group(1).strip()
            for attr_match in _FEISHU_AT_ID_ATTR_RE.finditer(attrs)
            if attr_match.group(1).strip()
        }
        items.append({"name": display_name, "ids": "\n".join(sorted(candidate_ids))})
    return items


def _extract_feishu_leading_plain_mentions(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    remaining = text
    while True:
        if not remaining.startswith(("@", "\uff20")):
            break
        parts = remaining.split(maxsplit=1)
        token = parts[0]
        items.append({"name": token[1:].strip().casefold(), "ids": ""})
        if len(parts) == 1:
            break
        remaining = parts[1].strip()
    return items


def _feishu_leading_mentions_include_bot(
    leading_mentions: list[dict[str, str]],
    *,
    mentions: Any,
    bot_ids: set[str],
    bot_names: set[str],
) -> bool:
    for mention in leading_mentions:
        mention_ids = {part for part in (mention.get("ids") or "").split("\n") if part}
        mention_name = mention.get("name") or ""
        if mention_ids and bot_ids and mention_ids.intersection(bot_ids):
            return True
        if mention_name and bot_names and mention_name in bot_names:
            return True

    if not isinstance(mentions, list):
        return False

    for mention in mentions[: len(leading_mentions)]:
        mention_name = str(_read_field(mention, "name") or "").strip().casefold()
        mention_ids = _read_feishu_mention_ids(mention)
        if mention_ids and bot_ids and mention_ids.intersection(bot_ids):
            return True
        if mention_name and bot_names and mention_name in bot_names:
            return True

    return False


def _read_feishu_mention_ids(mention: Any) -> set[str]:
    values: set[str] = set()
    mention_id = _read_field(mention, "id")
    for source in (mention, mention_id):
        for key in ("user_id", "open_id", "union_id"):
            value = _read_field(source, key)
            if isinstance(value, str) and value.strip():
                values.add(value.strip())
    return values


def _extract_dingtalk_text(payload: dict[str, Any]) -> str:
    text_obj = payload.get("text")
    if isinstance(text_obj, dict):
        content = text_obj.get("content")
        if isinstance(content, str):
            return content.strip()

    content = payload.get("content")
    if isinstance(content, str):
        return content.strip()

    return ""


def _dingtalk_at_users_include_bot(*, at_users: Any, bot_user_id: str | None) -> bool:
    target = (bot_user_id or "").strip()
    if not target or not isinstance(at_users, list):
        return False

    for user in at_users:
        for key in (
            "dingtalkId",
            "dingtalk_id",
            "staffId",
            "staff_id",
            "userId",
            "user_id",
        ):
            value = _read_field(user, key)
            if isinstance(value, str) and value.strip() == target:
                return True
    return False


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _normalize_im_text(text: str) -> str:
    return (text or "").replace("\u2005", " ").replace("\u2006", " ").strip()


def _read_field(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _try_dump_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            dumped = None
        if isinstance(dumped, dict):
            return dumped

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            dumped = to_dict()
        except Exception:
            dumped = None
        if isinstance(dumped, dict):
            return dumped

    return None


def _parse_receive_target(destination: str) -> tuple[str, str]:
    raw = (destination or "").strip()
    if not raw:
        return "chat_id", ""

    prefix, sep, value = raw.partition(":")
    if sep and prefix in {"chat_id", "open_id", "user_id", "union_id", "email"}:
        return prefix, value.strip()

    return "chat_id", raw


def _parse_positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            parsed = int(stripped)
            if parsed > 0:
                return parsed
    return default


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
