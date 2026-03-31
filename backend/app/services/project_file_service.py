import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.project_file import ProjectFile
from app.repositories.project_file_repository import ProjectFileRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project_file import ProjectFileAddRequest, ProjectFileResponse
from app.services.storage_service import S3StorageService

logger = logging.getLogger(__name__)


class ProjectFileService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self.storage_service = storage_service or S3StorageService()

    def list_project_files(
        self,
        db: Session,
        *,
        project_id: UUID,
        user_id: str,
    ) -> list[ProjectFileResponse]:
        self._get_project_owned_by_user(db, project_id=project_id, user_id=user_id)
        items = ProjectFileRepository.list_by_project(db, project_id)
        return [ProjectFileResponse.model_validate(item) for item in items]

    def add_file(
        self,
        db: Session,
        *,
        project_id: UUID,
        user_id: str,
        request: ProjectFileAddRequest,
    ) -> ProjectFileResponse:
        self._get_project_owned_by_user(db, project_id=project_id, user_id=user_id)
        item = ProjectFile(
            project_id=project_id,
            file_name=request.file_name,
            file_source=request.file_source,
            file_size=request.file_size,
            file_content_type=request.file_content_type,
            sort_order=ProjectFileRepository.get_max_sort_order(db, project_id) + 1,
        )
        ProjectFileRepository.create(db, item)
        db.commit()
        db.refresh(item)
        return ProjectFileResponse.model_validate(item)

    def remove_file(
        self,
        db: Session,
        *,
        project_id: UUID,
        user_id: str,
        file_id: int,
    ) -> None:
        self._get_project_owned_by_user(db, project_id=project_id, user_id=user_id)
        item = ProjectFileRepository.get_by_id(db, file_id)
        if item is None or item.project_id != project_id:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message=f"Project file not found: {file_id}",
            )

        file_source = item.file_source
        ProjectFileRepository.delete(db, item)
        db.commit()

        try:
            self.storage_service.delete_object(key=file_source)
        except AppException as exc:
            logger.warning(
                "Failed to delete project file object %s after DB removal: %s",
                file_source,
                exc.message,
            )

    @staticmethod
    def _get_project_owned_by_user(
        db: Session,
        *,
        project_id: UUID,
        user_id: str,
    ):
        project = ProjectRepository.get_by_id(db, project_id)
        if not project or project.user_id != user_id:
            raise AppException(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                message=f"Project not found: {project_id}",
            )
        return project
