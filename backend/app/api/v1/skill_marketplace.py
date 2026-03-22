from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill_import import SkillImportDiscoverResponse
from app.schemas.skill_marketplace import (
    SkillsMpImportDiscoverRequest,
    SkillsMpMarketplaceStatusResponse,
    SkillsMpRecommendationsResponse,
    SkillsMpSearchResponse,
)
from app.services.marketplace import SkillsMpService
from app.services.skill_import_service import SkillImportService

router = APIRouter(prefix="/skills/marketplace", tags=["skills"])

skillsmp_service = SkillsMpService()
import_service = SkillImportService()


@router.get(
    "/status",
    response_model=ResponseSchema[SkillsMpMarketplaceStatusResponse],
)
async def get_skills_marketplace_status(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skillsmp_service.get_marketplace_status(db, user_id=user_id)
    return Response.success(data=result, message="SkillsMP marketplace status loaded")


@router.get(
    "/search",
    response_model=ResponseSchema[SkillsMpSearchResponse],
)
async def search_skills_marketplace(
    q: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    semantic: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = await skillsmp_service.search(
        db=db,
        user_id=user_id,
        query=q,
        page=page,
        page_size=page_size,
        semantic=semantic,
    )
    return Response.success(
        data=result, message="SkillsMP search completed successfully"
    )


@router.get(
    "/recommendations",
    response_model=ResponseSchema[SkillsMpRecommendationsResponse],
)
async def list_skills_marketplace_recommendations(
    limit: int = Query(default=9, ge=1, le=24),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = await skillsmp_service.list_recommendations(
        db=db,
        user_id=user_id,
        limit=limit,
    )
    return Response.success(
        data=result,
        message="SkillsMP recommendations completed successfully",
    )


@router.post(
    "/import/discover",
    response_model=ResponseSchema[SkillImportDiscoverResponse],
)
def discover_skills_marketplace_import(
    request: SkillsMpImportDiscoverRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> JSONResponse:
    github_url = skillsmp_service.build_import_github_url(request.item)
    archive_source = skillsmp_service.build_import_source(request.item)
    result = import_service.discover(
        db,
        user_id=user_id,
        file=None,
        github_url=github_url,
        archive_source_override=archive_source,
    )
    preselected_relative_path = skillsmp_service.match_preselected_relative_path(
        result.candidates,
        request.item.relative_skill_path,
    )
    response = result.model_copy(
        update={
            "preselected_relative_path": preselected_relative_path,
            "skillsmp_item": request.item,
        }
    )
    return Response.success(data=response, message="SkillsMP import discovered")
