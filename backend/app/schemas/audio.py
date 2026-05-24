from pydantic import BaseModel


class AudioTranscriptionResponse(BaseModel):
    text: str


class AudioTranscriptionSupportResponse(BaseModel):
    available: bool
