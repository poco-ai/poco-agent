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
        self._app_id = (settings.feishu_app_id or "").strip()
        self._app_secret = (settings.feishu_app_secret or "").strip()
        self._base_url = settings.feishu_open_base_url.rstrip("/")
        self._enabled = bool(
            settings.feishu_enabled and self._app_id and self._app_secret
        )
        self._token_lock = asyncio.Lock()
        self._tenant_access_token: str | None = None
        self._token_expire_ts = 0.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _refresh_tenant_access_token(self) -> None:
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
        code = data.get("code")
        token = data.get("tenant_access_token")
        expire = data.get("expire")
        if code != 0 or not token:
            raise RuntimeError(f"Feishu auth failed: code={code} msg={data.get('msg')}")

        ttl = int(expire) if isinstance(expire, int) and expire > 0 else 7200
        self._tenant_access_token = str(token)
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
                raise RuntimeError("Feishu token is empty")
            return self._tenant_access_token

    async def send_text(self, *, destination: str, text: str) -> None:
        if not self._enabled:
            return

        try:
            token = await self._get_tenant_access_token()
        except Exception:
            logger.exception("feishu_auth_error")
            return

        url = f"{self._base_url}/open-apis/im/v1/messages"
        params = {"receive_id_type": "chat_id"}
        payload = {
            "receive_id": destination,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            resp = await client.post(url, params=params, json=payload, headers=headers)
        if not resp.is_success:
            logger.warning(
                "feishu_send_failed",
                extra={"status_code": resp.status_code, "response": resp.text[:300]},
            )
            return

        data = resp.json()
        if data.get("code") != 0:
            logger.warning(
                "feishu_send_failed",
                extra={"code": data.get("code"), "msg": data.get("msg")},
            )
