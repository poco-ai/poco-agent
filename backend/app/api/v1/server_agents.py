import uuid
import mimetypes

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.agent_identity import (
    AgentIdentityCreateRequest,
    AgentIdentityResponse,
    AgentRuntimePinRequest,
    AgentIdentityUpdateRequest,
    ChannelAgentMemberCreateRequest,
    ChannelAgentMemberResponse,
)
from app.schemas.response import Response, ResponseSchema
from app.schemas.workspace import FileNode
from app.services.agent_state_browser_service import AgentStateBrowserService
from app.services.agent_identity_service import AgentIdentityService

router = APIRouter(prefix="/servers/{server_id}/agents", tags=["server-agents"])
channel_router = APIRouter(
    prefix="/servers/{server_id}/channels/{channel_id}/agents",
    tags=["server-channel-agents"],
)

service = AgentIdentityService()
agent_state_browser_service = AgentStateBrowserService()


@router.get("", response_model=ResponseSchema[list[AgentIdentityResponse]])
async def list_server_agents(
    server_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_agents(db, current_user, server_id)
    return Response.success(data=result, message="Server agents retrieved successfully")


@router.post("", response_model=ResponseSchema[AgentIdentityResponse])
async def create_server_agent(
    server_id: uuid.UUID,
    request: AgentIdentityCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.create_agent(db, current_user, server_id, request)
    return Response.success(data=result, message="Server agent created successfully")


@router.get(
    "/{agent_identity_id}", response_model=ResponseSchema[AgentIdentityResponse]
)
async def get_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.get_agent(db, current_user, server_id, agent_identity_id)
    return Response.success(data=result, message="Server agent retrieved successfully")


@router.patch(
    "/{agent_identity_id}",
    response_model=ResponseSchema[AgentIdentityResponse],
)
async def update_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    request: AgentIdentityUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.update_agent(
        db, current_user, server_id, agent_identity_id, request
    )
    return Response.success(data=result, message="Server agent updated successfully")


@router.post(
    "/{agent_identity_id}/restart",
    response_model=ResponseSchema[AgentIdentityResponse],
)
async def restart_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.restart_agent(db, current_user, server_id, agent_identity_id)
    return Response.success(data=result, message="Server agent restarted successfully")


@router.post(
    "/{agent_identity_id}/stop",
    response_model=ResponseSchema[AgentIdentityResponse],
)
async def stop_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.stop_agent(db, current_user, server_id, agent_identity_id)
    return Response.success(data=result, message="Server agent stopped successfully")


@router.post(
    "/{agent_identity_id}/pin",
    response_model=ResponseSchema[AgentIdentityResponse],
)
async def pin_server_agent_runtime(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    request: AgentRuntimePinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.pin_agent_runtime(
        db,
        current_user,
        server_id,
        agent_identity_id,
        request,
    )
    return Response.success(
        data=result,
        message="Server agent runtime pinned successfully",
    )


@router.delete(
    "/{agent_identity_id}/pin",
    response_model=ResponseSchema[AgentIdentityResponse],
)
async def unpin_server_agent_runtime(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.unpin_agent_runtime(
        db,
        current_user,
        server_id,
        agent_identity_id,
    )
    return Response.success(
        data=result,
        message="Server agent runtime unpinned successfully",
    )


@router.delete("/{agent_identity_id}", response_model=ResponseSchema[dict])
async def remove_server_agent(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.remove_agent_from_server(db, current_user, server_id, agent_identity_id)
    return Response.success(
        data={"agent_identity_id": agent_identity_id},
        message="Server agent removed successfully",
    )


def _attach_agent_state_file_urls(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    nodes: list[FileNode],
) -> list[FileNode]:
    result: list[FileNode] = []
    for node in nodes:
        children = (
            _attach_agent_state_file_urls(server_id, agent_identity_id, node.children)
            if node.children
            else None
        )
        url = node.url
        if node.type == "file":
            url = (
                f"/api/v1/servers/{server_id}/agents/{agent_identity_id}/state-file"
                f"?path={node.path}"
            )
        result.append(node.model_copy(update={"children": children, "url": url}))
    return result


@router.get(
    "/{agent_identity_id}/state-files",
    response_model=ResponseSchema[list[FileNode]],
)
async def list_server_agent_state_files(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    nodes = agent_state_browser_service.list_files(
        db,
        server_id=server_id,
        agent_identity_id=agent_identity_id,
        current_user_id=current_user.id,
    )
    nodes = _attach_agent_state_file_urls(server_id, agent_identity_id, nodes)
    return Response.success(
        data=nodes,
        message="Server agent state files retrieved successfully",
    )


@router.get("/{agent_identity_id}/state-file")
async def get_server_agent_state_file(
    server_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    path: str = Query(...),
    disposition: str = Query(default="inline"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_path = agent_state_browser_service.resolve_file(
        db,
        server_id=server_id,
        agent_identity_id=agent_identity_id,
        current_user_id=current_user.id,
        path=path,
    )
    media_type, _ = mimetypes.guess_type(file_path.name)
    return FileResponse(
        path=file_path,
        media_type=media_type or "application/octet-stream",
        filename=file_path.name,
        content_disposition_type="attachment"
        if disposition == "attachment"
        else "inline",
    )


@channel_router.get("", response_model=ResponseSchema[list[AgentIdentityResponse]])
async def list_channel_agents(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.list_channel_agents(db, current_user, server_id, channel_id)
    return Response.success(
        data=result, message="Channel agents retrieved successfully"
    )


@channel_router.post("", response_model=ResponseSchema[ChannelAgentMemberResponse])
async def add_agent_to_channel(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    request: ChannelAgentMemberCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = service.add_agent_to_channel(
        db,
        current_user,
        server_id,
        channel_id,
        request,
    )
    return Response.success(data=result, message="Channel agent added successfully")


@channel_router.delete("/{agent_identity_id}", response_model=ResponseSchema[dict])
async def remove_agent_from_channel(
    server_id: uuid.UUID,
    channel_id: uuid.UUID,
    agent_identity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    service.remove_agent_from_channel(
        db,
        current_user,
        server_id,
        channel_id,
        agent_identity_id,
    )
    return Response.success(
        data={"agent_identity_id": agent_identity_id},
        message="Channel agent removed successfully",
    )
