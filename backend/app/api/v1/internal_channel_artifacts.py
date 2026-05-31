import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.schemas.channel_artifact import (
    AgentChannelArtifactDownloadRequest,
    AgentChannelArtifactReadRequest,
    AgentChannelArtifactSearchRequest,
    AgentChannelArtifactTextRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.channel_artifact_service import ChannelArtifactService

router = APIRouter(prefix="/internal/channel-artifacts", tags=["internal"])
service = ChannelArtifactService()


@router.get("/list", response_model=ResponseSchema[dict])
async def list_channel_artifacts_internal(
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_runtime_artifacts(db, session_id=session_id)
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifacts listed",
    )


@router.post("/read", response_model=ResponseSchema[dict])
async def read_channel_artifact_internal(
    request: AgentChannelArtifactReadRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.read_runtime_artifact(
        db,
        session_id=session_id,
        artifact_id=request.artifact_id,
        logical_path=request.logical_path,
        max_bytes=request.max_bytes,
    )
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifact read",
    )


@router.post("/search", response_model=ResponseSchema[dict])
async def search_channel_artifacts_internal(
    request: AgentChannelArtifactSearchRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.search_runtime_artifacts(
        db,
        session_id=session_id,
        query=request.query,
        limit=request.limit,
        include_content=request.include_content,
    )
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifacts searched",
    )


@router.post("/text", response_model=ResponseSchema[dict])
async def read_channel_artifact_text_internal(
    request: AgentChannelArtifactTextRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.read_runtime_artifact_text(
        db,
        session_id=session_id,
        artifact_id=request.artifact_id,
        logical_path=request.logical_path,
        start_char=request.start_char,
        max_chars=request.max_chars,
    )
    return Response.success(
        data=result.model_dump(mode="json"),
        message="Agent channel artifact text read",
    )


@router.post("/download")
async def download_channel_artifact_internal(
    request: AgentChannelArtifactDownloadRequest,
    session_id: uuid.UUID,
    _: None = Depends(require_internal_token),
    db: Session = Depends(get_db),
) -> FastAPIResponse:
    result = service.download_runtime_artifact(
        db,
        session_id=session_id,
        artifact_id=request.artifact_id,
        logical_path=request.logical_path,
    )
    artifact_id = getattr(
        result.artifact,
        "artifact_id",
        getattr(result.artifact, "id", None),
    )
    headers = {
        "X-Artifact-Id": str(artifact_id),
        "X-Artifact-Display-Name": result.filename,
        "X-Artifact-Logical-Path": result.artifact.logical_path,
        "X-Artifact-Mime-Type": result.media_type,
    }
    if result.artifact.size_bytes is not None:
        headers["X-Artifact-Size-Bytes"] = str(result.artifact.size_bytes)
    return FastAPIResponse(
        content=result.content,
        media_type=result.media_type,
        headers=headers,
    )
