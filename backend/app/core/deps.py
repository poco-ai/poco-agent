import uuid
from typing import Generator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


auth_service = AuthService()


def _is_valid_internal_token(x_internal_token: str | None) -> bool:
    settings = get_settings()
    return bool(
        settings.internal_api_token
        and x_internal_token
        and x_internal_token == settings.internal_api_token
    )


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> str:
    """Resolve the current user id from session auth or trusted internal headers."""
    settings = get_settings()
    session_token = request.cookies.get(
        settings.auth_cookie_name
    ) or _extract_bearer_token(authorization)
    if session_token:
        user_session = auth_service.authenticate_session_token(db, session_token)
        if user_session and user_session.user_id:
            return user_session.user_id
        raise HTTPException(status_code=401, detail="Authentication required")

    if _is_valid_internal_token(x_internal_token):
        value = (x_user_id or "").strip()
        if value:
            return value

    if auth_service.is_single_user_mode_effective():
        return auth_service.ensure_single_user(db).id

    raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current authenticated user model."""
    user = UserRepository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """Validate X-Internal-Token header for internal API endpoints."""
    settings = get_settings()
    if not settings.internal_api_token:
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Internal API token is not configured",
        )
    if not _is_valid_internal_token(x_internal_token):
        raise AppException(
            error_code=ErrorCode.FORBIDDEN,
            message="Invalid internal token",
        )


def get_user_id_by_session_id(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> str:
    """Resolve user id by session id for internal APIs."""
    db_session = SessionRepository.get_by_id(db, session_id)
    if not db_session:
        raise AppException(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Session not found: {session_id}",
        )
    return db_session.user_id
