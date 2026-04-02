import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_internal_token
from app.models.agent_run import AgentRun
from app.repositories.run_repository import RunRepository

router = APIRouter(prefix="/internal/runs", tags=["internal-runs"])


class RunMetadataUpdateRequest(BaseModel):
    permission_policy_snapshot: dict[str, Any] | None = None
    resolved_hook_specs: list[dict[str, Any]] | None = None
    config_layers: dict[str, Any] | None = None


@router.patch("/{run_id}/metadata")
def update_run_metadata(
    run_id: uuid.UUID,
    req: RunMetadataUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_internal_token),
) -> dict[str, str]:
    db_run = RunRepository.get_by_id(db, run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if req.permission_policy_snapshot is not None:
        db_run.permission_policy_snapshot = req.permission_policy_snapshot
    if req.resolved_hook_specs is not None:
        db_run.resolved_hook_specs = req.resolved_hook_specs
    if req.config_layers is not None:
        db_run.config_layers = req.config_layers

    db.flush()
    db.commit()
    return {"status": "ok"}
