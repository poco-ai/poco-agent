import uuid

from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.repositories.deliverable_repository import DeliverableRepository
from app.repositories.deliverable_version_repository import (
    DeliverableVersionRepository,
)
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.schemas.deliverable import DeliverableResponse, DeliverableVersionResponse
from app.schemas.tool_execution import ToolExecutionResponse


class DeliverableService:
    """Session-scoped deliverable query service."""

    def list_by_session(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
    ) -> list[DeliverableResponse]:
        return [
            DeliverableResponse.model_validate(item)
            for item in DeliverableRepository.list_by_session(db, session_id)
        ]

    def get_deliverable(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        deliverable_id: uuid.UUID,
    ) -> DeliverableResponse:
        deliverable = DeliverableRepository.get_by_id(db, deliverable_id)
        if deliverable is None or deliverable.session_id != session_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Deliverable not found: {deliverable_id}",
            )
        return DeliverableResponse.model_validate(deliverable)

    def list_versions_by_deliverable(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        deliverable_id: uuid.UUID,
    ) -> list[DeliverableVersionResponse]:
        deliverable = DeliverableRepository.get_by_id(db, deliverable_id)
        if deliverable is None or deliverable.session_id != session_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Deliverable not found: {deliverable_id}",
            )
        return [
            DeliverableVersionResponse.model_validate(item)
            for item in DeliverableVersionRepository.list_by_deliverable(
                db,
                deliverable_id,
            )
        ]

    def get_version(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> DeliverableVersionResponse:
        version = DeliverableVersionRepository.get_by_id(db, version_id)
        if version is None or version.session_id != session_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Deliverable version not found: {version_id}",
            )
        return DeliverableVersionResponse.model_validate(version)

    def get_version_tool_executions(
        self,
        db: Session,
        *,
        session_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> list[ToolExecutionResponse]:
        version = DeliverableVersionRepository.get_by_id(db, version_id)
        if version is None or version.session_id != session_id:
            raise AppException(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Deliverable version not found: {version_id}",
            )

        raw_ids = version.related_tool_execution_ids_json or {}
        ordered_ids: list[uuid.UUID] = []
        for bucket in ("strong", "moderate"):
            values = raw_ids.get(bucket)
            if not isinstance(values, list):
                continue
            for value in values:
                try:
                    ordered_ids.append(uuid.UUID(str(value)))
                except (TypeError, ValueError):
                    continue

        executions = ToolExecutionRepository.list_by_ids(db, ordered_ids)
        return [ToolExecutionResponse.model_validate(item) for item in executions]
