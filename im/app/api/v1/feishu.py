import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.schemas.response import Response
from app.services.feishu_event_parser import parse_feishu_webhook_event
from app.services.inbound_message_service import InboundMessageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/feishu", tags=["feishu"])


@router.post("")
async def webhook(request: Request):
    settings = get_settings()
    if not settings.feishu_enabled:
        return Response.success(data={"ok": True, "ignored": "provider_disabled"})

    try:
        payload = await request.json()
    except Exception:
        return Response.error(code=400, message="Invalid payload", status_code=400)
    if not isinstance(payload, dict):
        return Response.error(code=400, message="Invalid payload", status_code=400)

    challenge = payload.get("challenge")
    if isinstance(challenge, str) and challenge:
        expected = (settings.feishu_verification_token or "").strip()
        provided = _extract_verification_token(payload)
        if expected and provided != expected:
            return JSONResponse(
                status_code=403,
                content={"code": 403, "msg": "invalid verification token"},
            )
        return JSONResponse(status_code=200, content={"challenge": challenge})

    if "encrypt" in payload:
        return Response.error(
            code=400,
            message=(
                "Encrypted Feishu callbacks are not supported. "
                "Disable callback encryption in the Feishu app settings."
            ),
            status_code=400,
        )

    expected = (settings.feishu_verification_token or "").strip()
    provided = _extract_verification_token(payload)
    if expected and provided != expected:
        return JSONResponse(
            status_code=403,
            content={"code": 403, "msg": "invalid verification token"},
        )

    inbound = parse_feishu_webhook_event(payload)
    if inbound is None:
        return JSONResponse(status_code=200, content={"code": 0, "msg": "ignored"})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return JSONResponse(status_code=200, content={"code": 0, "msg": "ok"})


def _extract_verification_token(payload: dict[str, Any]) -> str:
    token = payload.get("token")
    if isinstance(token, str):
        return token.strip()

    header = payload.get("header")
    if isinstance(header, dict):
        header_token = header.get("token")
        if isinstance(header_token, str):
            return header_token.strip()

    return ""
