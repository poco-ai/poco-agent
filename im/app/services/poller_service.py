import asyncio
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.settings import get_settings
from app.repositories.active_session_repository import ActiveSessionRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.channel_delivery_repository import ChannelDeliveryRepository
from app.repositories.dedup_repository import DedupRepository
from app.repositories.watch_repository import WatchRepository
from app.services.backend_client import BackendClient, BackendClientError
from app.services.message_formatter import MessageFormatter
from app.services.notification_gateway import NotificationGateway

logger = logging.getLogger(__name__)


class PollerService:
    """Background pollers for Backend state (sessions/runs/user-input-requests)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = BackendClient()
        self.formatter = MessageFormatter()
        self.gateway = NotificationGateway()

    async def run_user_input_loop(self) -> None:
        interval = max(0.2, float(self.settings.poll_user_input_interval_seconds))
        while True:
            try:
                await self._poll_user_input_requests()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_user_input_failed")
            await asyncio.sleep(interval)

    async def run_sessions_recent_loop(self) -> None:
        interval = max(1.0, float(self.settings.poll_sessions_recent_interval_seconds))
        while True:
            try:
                await self._poll_recent_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_sessions_recent_failed")
            await asyncio.sleep(interval)

    async def run_sessions_full_loop(self) -> None:
        interval = max(10.0, float(self.settings.poll_sessions_full_interval_seconds))
        while True:
            try:
                await self._poll_all_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("poll_sessions_full_failed")
            await asyncio.sleep(interval)

    def _get_target_channel_ids(self, db: Session, *, session_id: str) -> set[int]:
        target: set[int] = set()

        for ch in ChannelRepository.list_enabled(db):
            if ch.subscribe_all:
                target.add(ch.id)

        for watch in WatchRepository.list_by_session(db, session_id=session_id):
            target.add(watch.channel_id)

        for active in ActiveSessionRepository.list_by_session(
            db, session_id=session_id
        ):
            target.add(active.channel_id)

        return target

    async def _poll_user_input_requests(self) -> None:
        try:
            pending = await self.backend.list_user_input_requests()
        except BackendClientError as exc:
            logger.warning("backend_list_user_input_failed", extra={"error": str(exc)})
            return

        if not pending:
            return

        db = SessionLocal()
        try:
            for entry in pending:
                request_id = str(entry.get("id") or "").strip()
                session_id = str(entry.get("session_id") or "").strip()
                tool_name = str(entry.get("tool_name") or "").strip()
                tool_input = entry.get("tool_input")
                expires_at = entry.get("expires_at")
                status = str(entry.get("status") or "").strip()

                if not request_id or not session_id or status != "pending":
                    continue

                target_channel_ids = self._get_target_channel_ids(
                    db, session_id=session_id
                )
                if not target_channel_ids:
                    continue

                for channel_id in target_channel_ids:
                    key = f"ui:{channel_id}:{request_id}"
                    if DedupRepository.exists(db, key=key):
                        continue

                    text = self.formatter.format_user_input_request(
                        request_id=request_id,
                        session_id=session_id,
                        tool_name=tool_name,
                        tool_input=tool_input if isinstance(tool_input, dict) else None,
                        expires_at=str(expires_at) if expires_at else None,
                    )
                    await self._send_to_channel(db, channel_id=channel_id, text=text)
                    DedupRepository.put(db, key=key)
        finally:
            db.close()

    async def _poll_recent_sessions(self) -> None:
        # First page only. This captures newly created sessions quickly.
        await self._poll_sessions_page(limit=100, offset=0)

    async def _poll_all_sessions(self) -> None:
        # Full scan is best-effort and can be heavy; keep it periodic.
        limit = 100
        offset = 0
        while True:
            batch = await self._poll_sessions_page(limit=limit, offset=offset)
            if batch <= 0:
                break
            offset += limit

    async def _poll_sessions_page(self, *, limit: int, offset: int) -> int:
        try:
            sessions = await self.backend.list_sessions(
                limit=limit, offset=offset, kind="chat"
            )
        except BackendClientError as exc:
            logger.warning("backend_list_sessions_failed", extra={"error": str(exc)})
            return 0

        if not sessions:
            return 0

        db = SessionLocal()
        try:
            for item in sessions:
                session_id = str(item.get("session_id") or item.get("id") or "").strip()
                if not session_id:
                    continue
                status = str(item.get("status") or "").strip()
                title = str(item.get("title") or "").strip() or None

                if status not in {"completed", "failed", "canceled"}:
                    continue

                target_channel_ids = self._get_target_channel_ids(
                    db, session_id=session_id
                )
                if not target_channel_ids:
                    continue

                run_id, run_status, last_error = await self._get_latest_run_detail(
                    session_id=session_id
                )
                run_id = run_id or None
                run_status = run_status or status

                for channel_id in target_channel_ids:
                    dedup_key = f"run:{channel_id}:{run_id or session_id}:{run_status}"
                    if DedupRepository.exists(db, key=dedup_key):
                        continue
                    text = self.formatter.format_terminal_notification(
                        session_id=session_id,
                        title=title,
                        status=run_status,
                        run_id=run_id,
                        last_error=last_error,
                    )
                    await self._send_to_channel(db, channel_id=channel_id, text=text)
                    DedupRepository.put(db, key=dedup_key)
        finally:
            db.close()

        return len(sessions)

    async def _get_latest_run_detail(
        self, *, session_id: str
    ) -> tuple[str | None, str | None, str | None]:
        try:
            runs = await self.backend.list_runs_by_session(session_id=session_id)
        except BackendClientError:
            return None, None, None
        if not runs:
            return None, None, None
        latest = runs[-1]
        run_id = str(latest.get("run_id") or latest.get("id") or "").strip() or None
        run_status = str(latest.get("status") or "").strip() or None
        last_error = (
            str(latest.get("last_error") or "").strip() or None
            if run_status == "failed"
            else None
        )
        return run_id, run_status, last_error

    async def _send_to_channel(
        self, db: Session, *, channel_id: int, text: str
    ) -> None:
        from app.models.channel import Channel  # local import to avoid circulars

        ch: Channel | None = db.get(Channel, channel_id)
        if not ch or not ch.enabled:
            return
        destination = (
            ChannelDeliveryRepository.get_send_address(db, channel_id=channel_id)
            or ch.destination
        )
        await self.gateway.send_text(
            provider=ch.provider,
            destination=destination,
            text=text,
        )
