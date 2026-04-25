from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse


class UserAdminService:
    def list_users(self, db: Session) -> list[CurrentUserResponse]:
        users = UserRepository.list_all(db)
        return [CurrentUserResponse.model_validate(user) for user in users]

    def update_system_role(
        self,
        db: Session,
        *,
        target_user_id: str,
        system_role: str,
        actor_user_id: str,
    ) -> CurrentUserResponse:
        if system_role not in {"user", "admin"}:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Invalid system role: {system_role}",
            )
        user = UserRepository.get_by_id(db, target_user_id)
        if user is None:
            raise AppException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message=f"User not found: {target_user_id}",
            )
        if user.id == actor_user_id and system_role != "admin":
            raise AppException(
                error_code=ErrorCode.FORBIDDEN,
                message="Cannot remove your own admin role",
            )
        user.system_role = system_role
        db.commit()
        db.refresh(user)
        return CurrentUserResponse.model_validate(user)
