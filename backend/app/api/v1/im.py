from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.schemas.response import Response
from app.services.im import InboundMessageService
from app.services.im_providers import (
    parse_dingtalk_webhook_event,
    parse_feishu_webhook_event,
    parse_telegram_update,
)

router = APIRouter()


@router.post("/webhooks/telegram", tags=["telegram"])
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
):
    settings = get_settings()
    if settings.telegram_webhook_secret_token:
        if (
            not x_telegram_bot_api_secret_token
            or x_telegram_bot_api_secret_token != settings.telegram_webhook_secret_token
        ):
            return Response.error(
                code=403,
                message="Invalid webhook token",
                status_code=403,
            )

    payload = await request.json()
    inbound = parse_telegram_update(payload)
    if inbound is None:
        return Response.success(data={"ok": True, "ignored": True})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return Response.success(data={"ok": True})


@router.post("/webhooks/dingtalk", tags=["dingtalk"])
async def dingtalk_webhook(
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
    provided = _extract_dingtalk_token(
        request=request,
        payload=payload,
        query_token=token,
    )
    if expected and provided != expected:
        return Response.error(code=403, message="Invalid token", status_code=403)

    inbound = parse_dingtalk_webhook_event(payload)
    if inbound is None:
        return Response.success(data={"ok": True, "ignored": True})

    service = InboundMessageService()
    await service.handle_message(message=inbound)
    return Response.success(data={"ok": True})


@router.post("/webhooks/feishu", tags=["feishu"])
async def feishu_webhook(request: Request):
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
        provided = _extract_feishu_verification_token(payload)
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
    provided = _extract_feishu_verification_token(payload)
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


def _extract_dingtalk_token(
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


def _extract_feishu_verification_token(payload: dict[str, Any]) -> str:
    token = payload.get("token")
    if isinstance(token, str):
        return token.strip()

    header = payload.get("header")
    if isinstance(header, dict):
        header_token = header.get("token")
        if isinstance(header_token, str):
            return header_token.strip()

    return ""
