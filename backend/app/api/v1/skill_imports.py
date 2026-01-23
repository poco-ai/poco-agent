from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill_import import (
    SkillImportCommitRequest,
    SkillImportCommitResponse,
    SkillImportDiscoverResponse,
)
from app.services.skill_import_service import SkillImportService

router = APIRouter(prefix="/skills/import", tags=["skills"])

service = SkillImportService()


@router.post(
    "/discover",
    response_model=ResponseSchema[SkillImportDiscoverResponse],
)
async def discover_skill_import(
    file: UploadFile | None = File(default=None),
    github_url: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.discover(db, user_id=user_id, file=file, github_url=github_url)
    return Response.success(data=result, message="Skill import discovered")


@router.post(
    "/commit",
    response_model=ResponseSchema[SkillImportCommitResponse],
)
async def commit_skill_import(
    request: SkillImportCommitRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.commit(db, user_id=user_id, request=request)
    return Response.success(data=result, message="Skill import committed")
