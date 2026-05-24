import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.input_file import InputFile
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace import FileNode
from app.services.channel_artifact_service import ChannelArtifactService

router = APIRouter(
    prefix="/servers/{server_id}/channels/{channel_id}",
    tags=["server-channel-artifacts"],
)

service = ChannelArtifactService()


@router.get("/artifacts", response_model=ResponseSchema[list[FileNode]])
async def list_channel_artifacts(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_channel_artifact_nodes(
        db,
        current_user=current_user,
        server_id=server_id,
        channel_id=channel_id,
    )
    return Response.success(
        data=result,
        message="Channel artifacts retrieved successfully",
    )


@router.post("/artifacts/upload", response_model=ResponseSchema[InputFile])
async def upload_channel_artifact(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.upload_channel_artifact(
        db,
        current_user=current_user,
        server_id=server_id,
        channel_id=channel_id,
        file=file,
    )
    return Response.success(
        data=result,
        message="Channel artifact uploaded successfully",
    )
