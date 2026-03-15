import asyncio
import json
import logging
import time

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


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
