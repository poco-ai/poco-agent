from fastapi import APIRouter

from app.schemas.response import Response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return Response.success(data={"status": "healthy"})
