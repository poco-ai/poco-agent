from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.computer import ComputerScreenshotUploadResponse
from app.schemas.response import Response, ResponseSchema
from app.services.computer_service import ComputerService

router = APIRouter(prefix="/computer", tags=["computer"])

computer_service = ComputerService()


@router.post(
    "/screenshots",
    response_model=ResponseSchema[ComputerScreenshotUploadResponse],
)
async def upload_browser_screenshot(
    session_id: str = Form(...),
    run_id: str | None = Form(default=None),
    tool_use_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a browser screenshot produced by the executor."""
    raw = await file.read()
    payload = computer_service.upload_browser_screenshot(
        session_id=session_id,
        run_id=run_id,
        tool_use_id=tool_use_id,
        content_type=file.content_type or "image/png",
        data=raw,
    )
    return Response.success(data=payload.model_dump(), message="Screenshot uploaded")
