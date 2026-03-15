import json
import re
from typing import Any

from app.schemas.im_message import InboundMessage

_LEADING_MENTION_RE = re.compile(r"^(?:<at\s+[^>]*>.*?</at>\s*)+")


def parse_feishu_webhook_event(payload: dict[str, Any]) -> InboundMessage | None:
    header = payload.get("header")
    event = payload.get("event")
    return _build_inbound_message(header=header, event=event, raw=payload)


def parse_feishu_stream_event(data: Any) -> InboundMessage | None:
    header = _read_field(data, "header")
    event = _read_field(data, "event")
    raw = _try_dump_dict(data)
    return _build_inbound_message(header=header, event=event, raw=raw)


def extract_text(content: Any) -> str:
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


def extract_sender_id(sender: Any) -> str | None:
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


def clean_text(text: str) -> str:
    cleaned = (text or "").replace("\u2005", " ").replace("\u2006", " ").strip()
    while True:
        matched = _LEADING_MENTION_RE.match(cleaned)
        if not matched:
            break
        cleaned = cleaned[matched.end() :].strip()
    return cleaned


def _build_inbound_message(
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

    text = clean_text(extract_text(_read_field(message, "content")))
    if not text:
        text = "/help"

    message_id = str(
        _read_field(message, "message_id") or _read_field(header, "event_id") or ""
    ).strip()

    return InboundMessage(
        provider="feishu",
        destination=chat_id,
        message_id=message_id,
        sender_id=extract_sender_id(sender),
        text=text,
        raw=raw,
    )


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
