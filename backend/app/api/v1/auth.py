from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import AuthConfigResponse, CurrentUserResponse
from app.schemas.response import Response, ResponseSchema
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

service = AuthService()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


@router.get("/google/login")
async def login_with_google(
    request: Request,
    next_path: str | None = Query(default=None, alias="next"),
):
    return await service.start_login(request, "google", next_path)


@router.get("/github/login")
async def login_with_github(
    request: Request,
    next_path: str | None = Query(default=None, alias="next"),
):
    return await service.start_login(request, "github", next_path)


@router.get("/google/callback")
async def google_callback(
    request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    return await service.handle_callback(request, "google", db)


@router.get("/github/callback")
async def github_callback(
    request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    return await service.handle_callback(request, "github", db)


@router.get("/me", response_model=ResponseSchema[CurrentUserResponse])
async def get_current_account(
    user: User = Depends(get_current_user),
) -> JSONResponse:
    return Response.success(
        data=CurrentUserResponse.model_validate(user),
        message="Current user retrieved successfully",
    )


@router.get("/config", response_model=ResponseSchema[AuthConfigResponse])
async def get_auth_config() -> JSONResponse:
    return Response.success(
        data=service.get_auth_config(),
        message="Auth config retrieved successfully",
    )


@router.post("/logout", response_model=ResponseSchema[dict[str, bool]])
async def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    session_token = request.cookies.get(
        service._get_settings().auth_cookie_name
    ) or _extract_bearer_token(request.headers.get("authorization"))
    service.logout(db, session_token)
    response = Response.success(
        data={"ok": True},
        message="Logged out successfully",
    )
    service.clear_auth_cookie(response)
    return response
