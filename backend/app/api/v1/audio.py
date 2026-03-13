from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user_id
from app.schemas.audio import AudioTranscriptionResponse
from app.schemas.response import Response, ResponseSchema
from app.services.audio_transcription_service import AudioTranscriptionService

router = APIRouter(prefix="/audio", tags=["audio"])

audio_transcription_service = AudioTranscriptionService()


@router.post(
    "/transcriptions",
    response_model=ResponseSchema[AudioTranscriptionResponse],
)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    result = await audio_transcription_service.transcribe(
        file=file,
        language=language,
    )
    return Response.success(
        data=result,
        message="Audio transcribed successfully",
    )
