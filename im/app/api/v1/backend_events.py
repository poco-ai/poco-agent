from fastapi import APIRouter, Header

from app.core.settings import get_settings
from app.core.database import SessionLocal
from app.schemas.backend_event import BackendEvent
from app.schemas.response import Response
from app.services.backend_event_service import BackendEventService

router = APIRouter(prefix="/internal/backend-events", tags=["backend-events"])


@router.post("")
async def receive_backend_event(
    event: BackendEvent,
    x_im_event_token: str | None = Header(default=None, alias="X-IM-Event-Token"),
):
    settings = get_settings()
    expected = (settings.backend_event_token or "").strip()
    if not expected or x_im_event_token != expected:
        return Response.error(
            code=403,
            message="Invalid backend event token",
            status_code=403,
        )

    service = BackendEventService()
    db = SessionLocal()
    try:
        delivered = await service.process_event(db, event=event)
    finally:
        db.close()

    return Response.success(data={"ok": True, "delivered": delivered})
