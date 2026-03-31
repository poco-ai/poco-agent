import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.project_file import ProjectFileAddRequest, ProjectFileResponse
from app.schemas.response import Response, ResponseSchema
from app.services.project_file_service import ProjectFileService

router = APIRouter(prefix="/projects/{project_id}/files", tags=["project-files"])

service = ProjectFileService()


@router.get("", response_model=ResponseSchema[list[ProjectFileResponse]])
async def list_project_files(
    project_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_project_files(db, project_id=project_id, user_id=user_id)
    return Response.success(
        data=result,
        message="Project files retrieved successfully",
    )


@router.post("", response_model=ResponseSchema[ProjectFileResponse])
async def add_project_file(
    project_id: uuid.UUID,
    request: ProjectFileAddRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.add_file(
        db,
        project_id=project_id,
        user_id=user_id,
        request=request,
    )
    return Response.success(
        data=result,
        message="Project file added successfully",
    )


@router.delete("/{file_id}", response_model=ResponseSchema[dict])
async def remove_project_file(
    project_id: uuid.UUID,
    file_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.remove_file(
        db,
        project_id=project_id,
        user_id=user_id,
        file_id=file_id,
    )
    return Response.success(
        data={"project_id": project_id, "file_id": file_id},
        message="Project file removed successfully",
    )
