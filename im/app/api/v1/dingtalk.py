import logging
from typing import Any

from fastapi import APIRouter, Query, Request

from app.core.settings import get_settings
from app.schemas.im_message import InboundMessage
from app.schemas.response import Response
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/dingtalk", tags=["dingtalk"])


@router.post("")
async def webhook(
    request: Request,
    token: str | None = Query(default=None),
):
    payload = await request.json()
    if not isinstance(payload, dict):
        return Response.error(code=400, message="Invalid payload", status_code=400)

    settings = get_settings()
    if not settings.dingtalk_enabled:
        return Response.success(data={"ok": True, "ignored": "provider_disabled"})
    expected = (settings.dingtalk_webhook_token or "").strip()
    provided = _extract_token(request=request, payload=payload, query_token=token)
    if expected and provided != expected:
        return Response.error(code=403, message="Invalid token", status_code=403)

    inbound = _parse_dingtalk_event(payload)
    if inbound is None:
        return Response.success(data={"ok": True, "ignored": True})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return Response.success(data={"ok": True})


def _extract_token(
    *,
    request: Request,
    payload: dict[str, Any],
    query_token: str | None,
) -> str:
    if query_token:
        return query_token

    header_token = request.headers.get("X-DingTalk-Token")
    if header_token:
        return header_token

    payload_token = payload.get("token")
    if isinstance(payload_token, str):
        return payload_token

    return ""


def _parse_dingtalk_event(payload: dict[str, Any]) -> InboundMessage | None:
    text = _extract_text(payload)
    if not text:
        return None

    conversation_id = str(payload.get("conversationId") or "").strip()
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
    sender_id = (
        str(payload.get("senderStaffId") or payload.get("senderNick") or "").strip()
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


def _extract_text(payload: dict[str, Any]) -> str:
    text_obj = payload.get("text")
    if isinstance(text_obj, dict):
        content = text_obj.get("content")
        if isinstance(content, str):
            return content.strip()

    content = payload.get("content")
    if isinstance(content, str):
        return content.strip()

    return ""
