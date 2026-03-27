import re
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_session import AgentSession
from app.models.deliverable_version import DeliverableVersion
from app.repositories.deliverable_repository import DeliverableRepository
from app.repositories.deliverable_version_repository import (
    DeliverableVersionRepository,
)
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.services.storage_service import S3StorageService
from app.utils.workspace_manifest import extract_manifest_files, normalize_manifest_path

_DELIVERABLE_EXTENSIONS = {
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".pdf": "pdf",
}
_TRAILING_SUFFIX_PATTERNS = (
    re.compile(r"([_\-\s]v\d+)$", re.IGNORECASE),
    re.compile(r"(v\d+)$", re.IGNORECASE),
    re.compile(r"([_\-\s]final(?:-\d+)?)$", re.IGNORECASE),
    re.compile(r"([_\-\s]修订版)$"),
    re.compile(r"([_\-\s]最终版)$"),
    re.compile(r"([_\-\s]?\d{8})$"),
    re.compile(r"([_\-\s]?\d{14})$"),
)


def normalize_logical_name(file_name: str) -> str:
    """Normalize a deliverable file name to a logical display name."""
    base_name = PurePosixPath(file_name or "").name
    stem = PurePosixPath(base_name).stem.lower().strip(" _-.")
    if not stem:
        return PurePosixPath(base_name).stem or base_name

    value = stem
    changed = True
    while changed and value:
        changed = False
        for pattern in _TRAILING_SUFFIX_PATTERNS:
            next_value = pattern.sub("", value).strip(" _-.")
            if next_value != value:
                value = next_value
                changed = True
                break

    value = re.sub(r"[_\-\s]+", " ", value).strip()
    return value or (PurePosixPath(base_name).stem or base_name)


@dataclass(slots=True)
class DeliverableCandidate:
    session_id: uuid.UUID
    run_id: uuid.UUID
    source_message_id: int | None
    kind: str
    logical_name: str
    file_path: str
    file_name: str
    confidence: float
    mime_type: str | None = None
    input_refs_json: dict[str, Any] | None = None
    related_tool_execution_ids_json: dict[str, Any] | None = None
    detection_metadata_json: dict[str, Any] | None = None


class DeliverableDetectionService:
    """Rule-based deliverable detection and persistence helpers."""

    def __init__(self, storage_service: S3StorageService | None = None) -> None:
        self._storage_service = storage_service

    def _storage(self) -> S3StorageService:
        return self._storage_service or S3StorageService()

    @staticmethod
    def is_deliverable_candidate(
        *,
        file_path: str,
        mime_type: str | None = None,
    ) -> bool:
        ext = PurePosixPath(file_path or "").suffix.lower()
        if ext in _DELIVERABLE_EXTENSIONS:
            return True
        return bool(mime_type and mime_type.lower() == "application/pdf")

    @staticmethod
    def should_promote_reference_input(
        *,
        ref_type: str,
        materially_modified: bool,
        presented_as_result: bool,
    ) -> bool:
        return ref_type == "upload" and materially_modified and presented_as_result

    @staticmethod
    def select_primary_candidates(
        candidates: list[DeliverableCandidate],
    ) -> list[DeliverableCandidate]:
        grouped: dict[tuple[uuid.UUID, str, str], list[DeliverableCandidate]] = {}
        for candidate in candidates:
            key = (candidate.session_id, candidate.kind, candidate.logical_name)
            grouped.setdefault(key, []).append(candidate)

        selected: list[DeliverableCandidate] = []
        for items in grouped.values():
            ranked = sorted(
                items,
                key=lambda item: (item.confidence, item.file_name.lower()),
                reverse=True,
            )
            primary = ranked[0]
            others = ranked[1:]
            metadata = dict(primary.detection_metadata_json or {})
            if others:
                metadata["same_run_candidates"] = [
                    {
                        "file_path": item.file_path,
                        "confidence": item.confidence,
                    }
                    for item in others
                ]
            primary.detection_metadata_json = metadata or None
            selected.append(primary)
        return selected

    def persist_candidates(
        self,
        session_db: Session,
        candidates: list[DeliverableCandidate],
    ) -> list[DeliverableVersion]:
        selected = self.select_primary_candidates(candidates)
        persisted: list[DeliverableVersion] = []

        for candidate in selected:
            deliverable, _ = DeliverableRepository.get_or_create(
                session_db,
                session_id=candidate.session_id,
                kind=candidate.kind,
                logical_name=candidate.logical_name,
            )
            session_db.flush()

            existing = DeliverableVersionRepository.get_by_session_run_path(
                session_db,
                session_id=candidate.session_id,
                run_id=candidate.run_id,
                file_path=candidate.file_path,
            )
            if existing is not None:
                persisted.append(existing)
                continue

            latest_version = DeliverableVersionRepository.get_latest_by_deliverable(
                session_db,
                deliverable_id=deliverable.id,
            )
            next_version_no = (
                1 if latest_version is None else latest_version.version_no + 1
            )

            version = DeliverableVersionRepository.create(
                session_db,
                session_id=candidate.session_id,
                run_id=candidate.run_id,
                deliverable_id=deliverable.id,
                source_message_id=candidate.source_message_id,
                version_no=next_version_no,
                file_path=candidate.file_path,
                file_name=candidate.file_name,
                mime_type=candidate.mime_type,
                input_refs_json=candidate.input_refs_json,
                related_tool_execution_ids_json=candidate.related_tool_execution_ids_json,
                detection_metadata_json={
                    **(candidate.detection_metadata_json or {}),
                    "confidence": candidate.confidence,
                    "normalized_logical_name": candidate.logical_name,
                },
            )
            session_db.flush()

            if deliverable.latest_version_id is None or next_version_no > (
                latest_version.version_no if latest_version else 0
            ):
                deliverable.latest_version_id = version.id

            persisted.append(version)

        return persisted

    def detect_for_completed_run(
        self,
        session_db: Session,
        *,
        session: AgentSession,
        run: AgentRun,
    ) -> list[DeliverableVersion]:
        manifest_key = (session.workspace_manifest_key or "").strip()
        if not manifest_key:
            return []

        manifest = self._storage().get_manifest(manifest_key)
        manifest_files = extract_manifest_files(manifest)
        workspace_state = (session.state_patch or {}).get("workspace_state", {})
        file_changes = {
            str(item.get("path", "")).replace("\\", "/").lstrip("/"): item
            for item in workspace_state.get("file_changes", []) or []
            if isinstance(item, dict) and item.get("path")
        }
        input_paths = {
            str(item.get("path", "")).replace("\\", "/").lstrip("/")
            for item in (run.config_snapshot or {}).get("input_files", []) or []
            if isinstance(item, dict) and item.get("path")
        }
        tool_executions = ToolExecutionRepository.list_by_session(
            session_db,
            session.id,
            limit=2000,
        )

        candidates: list[DeliverableCandidate] = []
        for item in manifest_files:
            raw_path = normalize_manifest_path(item.get("path"))
            if not raw_path:
                continue

            normalized_path = raw_path.lstrip("/")
            file_name = PurePosixPath(normalized_path).name
            mime_type = item.get("mimeType") or item.get("mime_type")
            if not self.is_deliverable_candidate(
                file_path=normalized_path,
                mime_type=mime_type,
            ):
                continue

            materially_modified = normalized_path in file_changes
            if (
                normalized_path in input_paths
                and not self.should_promote_reference_input(
                    ref_type="upload",
                    materially_modified=materially_modified,
                    presented_as_result=True,
                )
            ):
                continue

            strong_ids: list[str] = []
            moderate_ids: list[str] = []
            for execution in tool_executions:
                haystacks = [
                    str(execution.tool_name or ""),
                    str(execution.tool_input or ""),
                    str(execution.tool_output or ""),
                ]
                combined = " ".join(haystacks)
                if normalized_path in combined or file_name in combined:
                    strong_ids.append(str(execution.id))
                elif normalize_logical_name(file_name) in combined.lower():
                    moderate_ids.append(str(execution.id))

            confidence = 0.5
            if materially_modified:
                confidence += 0.2
            if strong_ids:
                confidence += 0.2
            elif moderate_ids:
                confidence += 0.1
            if normalized_path not in input_paths:
                confidence += 0.1

            ext = PurePosixPath(normalized_path).suffix.lower()
            kind = _DELIVERABLE_EXTENSIONS.get(ext, "pdf")
            candidates.append(
                DeliverableCandidate(
                    session_id=session.id,
                    run_id=run.id,
                    source_message_id=run.user_message_id,
                    kind=kind,
                    logical_name=normalize_logical_name(file_name),
                    file_path=normalized_path,
                    file_name=file_name,
                    confidence=min(confidence, 0.99),
                    mime_type=mime_type,
                    input_refs_json={
                        "file_refs": [
                            {"path": path, "ref_type": "upload"}
                            for path in sorted(input_paths)
                        ],
                        "message_refs": [run.user_message_id],
                    },
                    related_tool_execution_ids_json={
                        "strong": strong_ids,
                        "moderate": moderate_ids,
                    },
                )
            )

        if not candidates:
            return []
        return self.persist_candidates(session_db, candidates)
