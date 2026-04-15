import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.project import (
    ProjectCopyRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.schemas.response import Response, ResponseSchema
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

service = ProjectService()


@router.get("", response_model=ResponseSchema[list[ProjectResponse]])
async def list_projects(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_projects(db, user_id)
    return Response.success(data=result, message="Projects retrieved successfully")


@router.get("/{project_id}", response_model=ResponseSchema[ProjectResponse])
async def get_project(
    project_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_project(db, user_id, project_id)
    return Response.success(data=result, message="Project retrieved successfully")


@router.post("", response_model=ResponseSchema[ProjectResponse])
async def create_project(
    request: ProjectCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_project(db, user_id, request)
    return Response.success(data=result, message="Project created successfully")


@router.post("/{project_id}/copy", response_model=ResponseSchema[ProjectResponse])
async def copy_project(
    project_id: uuid.UUID,
    request: ProjectCopyRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.copy_project(db, user_id, project_id, request)
    return Response.success(data=result, message="Project copied successfully")


@router.patch("/{project_id}", response_model=ResponseSchema[ProjectResponse])
async def update_project(
    project_id: uuid.UUID,
    request: ProjectUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_project(db, user_id, project_id, request)
    return Response.success(data=result, message="Project updated successfully")


@router.delete("/{project_id}", response_model=ResponseSchema[dict])
async def delete_project(
    project_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.delete_project(db, user_id, project_id)
    return Response.success(
        data={"id": project_id}, message="Project deleted successfully"
    )
