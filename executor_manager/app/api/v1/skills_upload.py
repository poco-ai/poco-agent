import asyncio

import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.core.deps import require_callback_token
from app.core.settings import get_settings
from app.schemas.response import Response, ResponseSchema
from app.services.backend_client import BackendClient
from app.services.workspace_export_service import WorkspaceExportService

router = APIRouter(prefix="/skills", tags=["skills"])
backend_client = BackendClient()
workspace_export_service = WorkspaceExportService()


class SkillSubmitRequest(BaseModel):
    session_id: str
    folder_path: str
    skill_name: str | None = None


async def _prepare_and_export_skill_folder(
    session_id: str,
    *,
    folder_path: str,
) -> tuple[str, str]:
    staged_folder_path = await asyncio.to_thread(
        workspace_export_service.stage_skill_submission_folder,
        session_id,
        folder_path=folder_path,
    )
    result = await asyncio.to_thread(
        workspace_export_service.export_workspace_folder,
        session_id,
        folder_path=staged_folder_path,
    )
    if result.workspace_export_status != "ready":
        raise HTTPException(
            status_code=400,
            detail=result.error or "Skill folder export failed",
        )
    workspace_files_prefix = (result.workspace_files_prefix or "").strip()
    if not workspace_files_prefix:
        raise HTTPException(
            status_code=400, detail="Skill folder export is missing files"
        )
    return staged_folder_path, workspace_files_prefix


@router.post("/submit", response_model=ResponseSchema[dict])
async def submit_skill(
    request: SkillSubmitRequest,
    _: None = Depends(require_callback_token),
) -> JSONResponse:
    folder_path, workspace_files_prefix = await _prepare_and_export_skill_folder(
        request.session_id,
        folder_path=request.folder_path,
    )
    try:
        response = await backend_client._request(
            "POST",
            "/api/v1/internal/skills/submit-from-workspace",
            params={"session_id": request.session_id},
            json={
                "folder_path": folder_path,
                "skill_name": request.skill_name,
                "workspace_files_prefix": workspace_files_prefix,
            },
            headers={
                "X-Internal-Token": get_settings().internal_api_token,
                **BackendClient._trace_headers(),
            },
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            payload = exc.response.json()
            detail = payload.get("message") or payload.get("detail") or detail
        except Exception:
            pass
        raise HTTPException(
            status_code=exc.response.status_code, detail=detail
        ) from exc

    payload = response.json()
    return Response.success(
        data=payload.get("data"),
        message=payload.get("message", "Skill submission queued successfully"),
    )
