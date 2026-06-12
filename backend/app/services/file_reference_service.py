from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.schemas.input_file import (
    FileReference,
    InputFile,
    InputFileReference,
    WorkspaceFileReference,
)
from app.services.storage_service import S3StorageService
from app.utils.workspace_manifest import find_manifest_file, normalize_manifest_path


class FileReferenceService:
    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self._storage_service = storage_service

    @property
    def storage_service(self) -> S3StorageService:
        if self._storage_service is None:
            self._storage_service = S3StorageService()
        return self._storage_service

    @staticmethod
    def get_config_references(config: Any) -> list[FileReference]:
        if config is None:
            return []
        references = getattr(config, "file_references", None) or getattr(
            config, "input_file_references", None
        )
        return list(references or [])

    @staticmethod
    def _input_file_from_raw(value: InputFile | dict[str, Any]) -> InputFile | None:
        if isinstance(value, InputFile):
            return value
        if not isinstance(value, dict):
            return None
        try:
            return InputFile.model_validate(value)
        except ValidationError:
            return None

    @staticmethod
    def _input_file_source(input_file: InputFile) -> str:
        return (input_file.source or "").strip()

    @staticmethod
    def _reference_from_raw(
        reference: FileReference | dict[str, Any],
    ) -> FileReference | None:
        if isinstance(reference, (InputFileReference, WorkspaceFileReference)):
            return reference
        if not isinstance(reference, dict):
            return None

        kind = str(reference.get("kind") or "").strip()
        try:
            if kind == "input_file":
                return InputFileReference.model_validate(reference)
            if kind == "workspace_file":
                return WorkspaceFileReference.model_validate(reference)
        except ValidationError:
            return None
        return None

    @staticmethod
    def _reference_to_dict(reference: FileReference) -> dict[str, Any]:
        return reference.model_dump(mode="json", by_alias=True)

    @classmethod
    def _collect_input_by_source(
        cls,
        input_files: list[InputFile] | list[dict[str, Any]],
    ) -> dict[str, InputFile]:
        by_source: dict[str, InputFile] = {}
        for raw_input_file in input_files:
            input_file = cls._input_file_from_raw(raw_input_file)
            if input_file is None:
                continue
            source = cls._input_file_source(input_file)
            if source and source not in by_source:
                by_source[source] = input_file
        return by_source

    @classmethod
    def _collect_historical_inputs(
        cls,
        db: Session,
        session_id: UUID,
    ) -> dict[str, InputFile]:
        by_source: dict[str, InputFile] = {}
        runs = (
            db.query(AgentRun)
            .filter(AgentRun.session_id == session_id)
            .order_by(AgentRun.created_at.asc())
            .all()
        )
        for run in runs:
            snapshot = run.config_snapshot or {}
            if not isinstance(snapshot, dict):
                continue
            raw_inputs = snapshot.get("input_files")
            if not isinstance(raw_inputs, list):
                continue
            for source, input_file in cls._collect_input_by_source(raw_inputs).items():
                by_source.setdefault(source, input_file)
        return by_source

    def _validate_workspace_reference(
        self,
        db_session: AgentSession,
        reference: WorkspaceFileReference,
    ) -> WorkspaceFileReference:
        if reference.session_id != str(db_session.id):
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="workspace_file reference must target the current session",
            )

        manifest_key = (db_session.workspace_manifest_key or "").strip()
        if db_session.workspace_export_status != "ready" or not manifest_key:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Session workspace export is not ready",
            )

        normalized_path = normalize_manifest_path(reference.path)
        if not normalized_path:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="Invalid workspace_file reference path",
            )

        manifest = self.storage_service.get_manifest(manifest_key)
        file_entry = find_manifest_file(manifest, normalized_path)
        if file_entry is None:
            raise AppException(
                error_code=ErrorCode.BAD_REQUEST,
                message="workspace_file reference path does not exist",
            )

        return reference.model_copy(update={"path": normalized_path})

    def resolve_for_run(
        self,
        db: Session,
        db_session: AgentSession,
        references: list[FileReference] | list[dict[str, Any]] | None,
        input_files: list[InputFile],
        *,
        prompt: str | None = None,
    ) -> tuple[list[InputFile], list[dict[str, Any]]]:
        if not references:
            return input_files, []

        merged_inputs = list(input_files)
        available_by_source = self._collect_input_by_source(merged_inputs)
        historical_by_source = self._collect_historical_inputs(db, db_session.id)
        normalized_references: list[dict[str, Any]] = []
        prompt_text = prompt or ""

        def add_input(input_file: InputFile) -> None:
            source = self._input_file_source(input_file)
            if not source or source in available_by_source:
                return
            available_by_source[source] = input_file
            merged_inputs.append(input_file)

        for raw_reference in references:
            reference = self._reference_from_raw(raw_reference)
            if reference is None:
                continue

            inserted_text = reference.inserted_text.strip()
            if (
                prompt is not None
                and inserted_text
                and inserted_text not in prompt_text
            ):
                continue

            if isinstance(reference, InputFileReference):
                source = reference.source.strip()
                input_file = available_by_source.get(
                    source
                ) or historical_by_source.get(source)
                if input_file is None:
                    raise AppException(
                        error_code=ErrorCode.BAD_REQUEST,
                        message="input_file reference source does not exist in this session",
                    )
                add_input(input_file)
            else:
                reference = self._validate_workspace_reference(db_session, reference)

            normalized_references.append(self._reference_to_dict(reference))

        return merged_inputs, normalized_references
