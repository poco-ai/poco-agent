import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.schemas.im_message import InboundMessage
from app.schemas.response import Response
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/feishu", tags=["feishu"])


@router.post("")
async def webhook(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        return Response.error(code=400, message="Invalid payload", status_code=400)

    settings = get_settings()

    if not settings.feishu_enabled:
        return Response.success(data={"ok": True, "ignored": "provider_disabled"})

    # URL verification handshake.
    if str(payload.get("type") or "") == "url_verification":
        token = str(payload.get("token") or "")
        expected = (settings.feishu_verification_token or "").strip()
        if expected and token != expected:
            return Response.error(code=403, message="Invalid token", status_code=403)
        challenge = payload.get("challenge")
        return JSONResponse(status_code=200, content={"challenge": challenge})

    if not _verify_token(
        payload, expected=(settings.feishu_verification_token or "").strip()
    ):
        return Response.error(code=403, message="Invalid token", status_code=403)

    inbound = _parse_feishu_event(payload)
    if inbound is None:
        return Response.success(data={"ok": True, "ignored": True})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return Response.success(data={"ok": True})


def _verify_token(payload: dict[str, Any], *, expected: str) -> bool:
    if not expected:
        return True

    token_candidates: list[str] = []
    raw_token = payload.get("token")
    if isinstance(raw_token, str):
        token_candidates.append(raw_token)

    header = payload.get("header")
    if isinstance(header, dict):
        header_token = header.get("token")
        if isinstance(header_token, str):
            token_candidates.append(header_token)

    return expected in token_candidates


def _parse_feishu_event(payload: dict[str, Any]) -> InboundMessage | None:
    header = payload.get("header")
    if not isinstance(header, dict):
        return None

    event_type = str(header.get("event_type") or "")
    if event_type != "im.message.receive_v1":
        return None

    event = payload.get("event")
    if not isinstance(event, dict):
        return None

    message = event.get("message")
    if not isinstance(message, dict):
        return None

    message_type = str(message.get("message_type") or "")
    if message_type != "text":
        return None

    content = message.get("content")
    text = _extract_feishu_text(content)
    if not text:
        return None

    chat_id = str(message.get("chat_id") or "").strip()
    if not chat_id:
        return None

    message_id = str(message.get("message_id") or header.get("event_id") or "").strip()

    sender_id = None
    sender = event.get("sender")
    if isinstance(sender, dict):
        sender_id_obj = sender.get("sender_id")
        if isinstance(sender_id_obj, dict):
            raw_sender_id = (
                sender_id_obj.get("open_id")
                or sender_id_obj.get("union_id")
                or sender_id_obj.get("user_id")
            )
            if raw_sender_id:
                sender_id = str(raw_sender_id)

    return InboundMessage(
        provider="feishu",
        destination=chat_id,
        send_address=chat_id,
        message_id=message_id,
        sender_id=sender_id,
        text=text,
        raw=payload,
    )


def _extract_feishu_text(content: Any) -> str:
    if isinstance(content, str):
        raw = content.strip()
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
        except Exception:
            return raw
        if isinstance(parsed, dict):
            val = parsed.get("text")
            if isinstance(val, str):
                return val.strip()
        return raw

    if isinstance(content, dict):
        val = content.get("text")
        if isinstance(val, str):
            return val.strip()

    return ""
