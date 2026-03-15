from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.core.database import SessionLocal
from app.core.observability.request_context import (
    generate_request_id,
    generate_trace_id,
)
from app.core.settings import get_settings
from app.repositories.im_event_outbox_repository import ImEventOutboxRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClaimedEvent:
    id: str
    event_type: str
    attempt_count: int
    payload: dict


class ImEventDispatcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        url = (self.settings.im_event_callback_url or "").strip()
        token = (self.settings.im_event_token or "").strip()
        return bool(self.settings.im_event_dispatch_enabled and url and token)

    async def run_forever(self) -> None:
        if not self.enabled:
            logger.info("im_event_dispatcher_disabled")
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0),
            trust_env=False,
        )
        interval = max(0.2, float(self.settings.im_event_dispatch_interval_seconds))
        try:
            while True:
                try:
                    await self._dispatch_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("im_event_dispatcher_iteration_failed")
                await asyncio.sleep(interval)
        finally:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def _dispatch_once(self) -> None:
        batch_size = max(1, int(self.settings.im_event_dispatch_batch_size))
        lease_seconds = max(5, int(self.settings.im_event_dispatch_lease_seconds))
        claimed = await asyncio.to_thread(
            self._claim_due_batch,
            batch_size,
            lease_seconds,
        )
        if not claimed:
            return

        for event in claimed:
            try:
                await self._deliver(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = min(60.0, float(2 ** min(event.attempt_count, 6)))
                await asyncio.to_thread(
                    self._mark_retry,
                    event.id,
                    str(exc),
                    delay,
                )
                logger.warning(
                    "im_event_delivery_failed",
                    extra={
                        "event_id": event.id,
                        "event_type": event.event_type,
                        "attempt_count": event.attempt_count,
                        "error": str(exc),
                    },
                )
            else:
                await asyncio.to_thread(self._mark_delivered, event.id)

    async def _deliver(self, event: ClaimedEvent) -> None:
        if self._client is None:
            raise RuntimeError("IM event dispatcher client is not initialized")

        callback_url = (self.settings.im_event_callback_url or "").strip()
        token = (self.settings.im_event_token or "").strip()
        response = await self._client.post(
            callback_url,
            json=event.payload,
            headers={
                "X-IM-Event-Token": token,
                "X-Request-ID": generate_request_id(),
                "X-Trace-ID": generate_trace_id(),
            },
        )
        response.raise_for_status()

    @staticmethod
    def _claim_due_batch(limit: int, lease_seconds: int) -> list[ClaimedEvent]:
        db = SessionLocal()
        try:
            rows = ImEventOutboxRepository.claim_due_batch(
                db,
                limit=limit,
                lease_seconds=lease_seconds,
            )
            claimed: list[ClaimedEvent] = []
            for row in rows:
                payload = row.payload if isinstance(row.payload, dict) else {}
                claimed.append(
                    ClaimedEvent(
                        id=str(row.id),
                        event_type=row.event_type,
                        attempt_count=int(row.attempt_count or 0),
                        payload=payload,
                    )
                )
            return claimed
        finally:
            db.close()

    @staticmethod
    def _mark_delivered(event_id: str) -> None:
        db = SessionLocal()
        try:
            ImEventOutboxRepository.mark_delivered(db, event_id=event_id)
        finally:
            db.close()

    @staticmethod
    def _mark_retry(event_id: str, error_message: str, delay_seconds: float) -> None:
        db = SessionLocal()
        try:
            ImEventOutboxRepository.mark_retry(
                db,
                event_id=event_id,
                error_message=error_message,
                delay_seconds=delay_seconds,
            )
        finally:
            db.close()
