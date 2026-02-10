import logging

import asyncio
import json
import time

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
        self._open_base_url = (settings.dingtalk_open_base_url or "").rstrip("/")
        self._app_key = (settings.dingtalk_app_key or "").strip()
        self._app_secret = (settings.dingtalk_app_secret or "").strip()
        self._robot_code = (settings.dingtalk_robot_code or "").strip()
        self._openapi_enabled = bool(
            self._open_base_url
            and self._app_key
            and self._app_secret
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
            "appKey": self._app_key,
            "appSecret": self._app_secret,
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
            # Prefer group send; fallback to private chat send for 1:1 conversations.
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

    async def send_text(self, *, destination: str, text: str) -> None:
        if not self._enabled:
            return

        dest = (destination or "").strip()
        if not dest:
            return

        # 1) Session webhook / custom robot webhook.
        if dest.startswith("http"):
            await self._send_via_webhook(url=dest, text=text)
            return

        # 2) Proactive send via OpenAPI (stable, based on conversationId).
        if await self._send_via_openapi(conversation_id=dest, text=text):
            return

        # 3) Fallback: a fixed outbound-only webhook (notifications only).
        if self._fallback_webhook:
            await self._send_via_webhook(url=self._fallback_webhook, text=text)
            return

        logger.warning(
            "dingtalk_send_skipped",
            extra={"reason": "no_route", "destination": dest},
        )
