import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_system_admin
from app.models.user import User
from app.schemas.admin import (
    ClaudeMdAdminUpsertRequest,
    ModelConfigAdminUpdateRequest,
    SystemRoleUpdateRequest,
)
from app.schemas.auth import CurrentUserResponse
from app.schemas.claude_md import ClaudeMdResponse, ClaudeMdUpsertRequest
from app.schemas.env_var import (
    SystemEnvVarAdminResponse,
    SystemEnvVarCreateRequest,
    SystemEnvVarUpdateRequest,
)
from app.schemas.mcp_server import (
    McpServerAdminResponse,
    McpServerCreateRequest,
    McpServerUpdateRequest,
)
from app.schemas.model_config import ModelConfigResponse
from app.schemas.plugin import (
    PluginAdminResponse,
    PluginCreateRequest,
    PluginUpdateRequest,
)
from app.schemas.plugin_import import (
    PluginImportCommitEnqueueResponse,
    PluginImportCommitRequest,
    PluginImportDiscoverResponse,
    PluginImportJobResponse,
)
from app.schemas.preset import (
    PresetAdminResponse,
    PresetCreateRequest,
    PresetResponse,
    PresetUpdateRequest,
    PresetVisualSummary,
)
from app.schemas.response import Response, ResponseSchema
from app.schemas.skill_import import (
    SkillImportCommitEnqueueResponse,
    SkillImportCommitRequest,
    SkillImportDiscoverResponse,
    SkillImportJobResponse,
)
from app.schemas.skill import SkillCreateRequest, SkillResponse, SkillUpdateRequest
from app.schemas.slash_command import (
    SlashCommandAdminResponse,
    SlashCommandCreateRequest,
    SlashCommandUpdateRequest,
)
from app.schemas.sub_agent import (
    SubAgentAdminResponse,
    SubAgentCreateRequest,
    SubAgentUpdateRequest,
)
from app.services.claude_md_service import ClaudeMdService
from app.services.env_var_service import EnvVarService
from app.services.mcp_server_service import McpServerService
from app.services.model_admin_service import ModelAdminService
from app.services.preset_service import PresetService
from app.services.plugin_service import PluginService
from app.services.plugin_import_job_service import (
    PluginImportJobService as PluginImportJobSvc,
)
from app.services.plugin_import_service import PluginImportService as PluginImportSvc
from app.services.skill_service import SkillService
from app.services.skill_import_job_service import SkillImportJobService
from app.services.skill_import_service import SkillImportService
from app.services.slash_command_service import SlashCommandService
from app.services.constants import SYSTEM_USER_ID
from app.services.sub_agent_service import SubAgentService
from app.services.user_admin_service import UserAdminService

router = APIRouter(prefix="/admin", tags=["admin"])

env_var_service = EnvVarService()
model_admin_service = ModelAdminService()
skill_service = SkillService()
skill_import_service = SkillImportService()
skill_import_job_service = SkillImportJobService(import_service=skill_import_service)
mcp_server_service = McpServerService()
plugin_service = PluginService()
plugin_import_service = PluginImportSvc()
plugin_import_job_service = PluginImportJobSvc(import_service=plugin_import_service)
user_admin_service = UserAdminService()
slash_command_service = SlashCommandService()
claude_md_service = ClaudeMdService()
preset_service = PresetService()
sub_agent_service = SubAgentService()


@router.get(
    "/system-env-vars", response_model=ResponseSchema[list[SystemEnvVarAdminResponse]]
)
async def list_system_env_vars(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = env_var_service.list_system_env_vars_for_admin(db)
    return Response.success(data=result, message="System env vars retrieved")


@router.post(
    "/system-env-vars", response_model=ResponseSchema[SystemEnvVarAdminResponse]
)
async def create_system_env_var(
    request: SystemEnvVarCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    created_result = env_var_service.create_system_env_var(db, request)
    result = env_var_service.list_system_env_vars_for_admin(db)
    created = next((item for item in result if item.id == created_result.id), None)
    if created is None:
        raise RuntimeError("Failed to load created system env var")
    return Response.success(data=created, message="System env var created")


@router.patch(
    "/system-env-vars/{env_var_id}",
    response_model=ResponseSchema[SystemEnvVarAdminResponse],
)
async def update_system_env_var(
    env_var_id: int,
    request: SystemEnvVarUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    env_var_service.update_system_env_var(db, env_var_id, request)
    result = env_var_service.list_system_env_vars_for_admin(db)
    updated = next((item for item in result if item.id == env_var_id), None)
    if updated is None:
        raise RuntimeError("Failed to load updated system env var")
    return Response.success(data=updated, message="System env var updated")


@router.delete("/system-env-vars/{env_var_id}", response_model=ResponseSchema[dict])
async def delete_system_env_var(
    env_var_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    env_var_service.delete_system_env_var(db, env_var_id)
    return Response.success(data={"id": env_var_id}, message="System env var deleted")


@router.get("/model-config", response_model=ResponseSchema[ModelConfigResponse])
async def get_model_config(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = model_admin_service.get_model_config(db)
    return Response.success(data=result, message="Model config retrieved")


@router.patch("/model-config", response_model=ResponseSchema[ModelConfigResponse])
async def update_model_config(
    request: ModelConfigAdminUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = model_admin_service.update_model_config(
        db,
        default_model=request.default_model,
        model_list=request.model_list,
    )
    return Response.success(data=result, message="Model config updated")


@router.get("/skills", response_model=ResponseSchema[list[SkillResponse]])
async def list_system_skills(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skill_service.list_skills(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System skills retrieved")


@router.post("/skills", response_model=ResponseSchema[SkillResponse])
async def create_system_skill(
    request: SkillCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    payload = request.model_copy(update={"scope": "system"})
    result = skill_service.create_skill(db, user_id=SYSTEM_USER_ID, request=payload)
    return Response.success(data=result, message="System skill created")


@router.patch("/skills/{skill_id}", response_model=ResponseSchema[SkillResponse])
async def update_system_skill(
    skill_id: int,
    request: SkillUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skill_service.update_skill(
        db, user_id=SYSTEM_USER_ID, skill_id=skill_id, request=request
    )
    return Response.success(data=result, message="System skill updated")


@router.delete("/skills/{skill_id}", response_model=ResponseSchema[dict])
async def delete_system_skill(
    skill_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    skill_service.delete_skill(db, user_id=SYSTEM_USER_ID, skill_id=skill_id)
    return Response.success(data={"id": skill_id}, message="System skill deleted")


@router.post(
    "/skills/import/discover",
    response_model=ResponseSchema[SkillImportDiscoverResponse],
)
def discover_system_skill_import(
    file: UploadFile | None = File(default=None),
    github_url: str | None = Form(default=None),
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skill_import_service.discover(
        db,
        user_id=SYSTEM_USER_ID,
        file=file,
        github_url=github_url,
    )
    return Response.success(data=result, message="System skill import discovered")


@router.post(
    "/skills/import/commit",
    response_model=ResponseSchema[SkillImportCommitEnqueueResponse],
)
def commit_system_skill_import(
    request: SkillImportCommitRequest,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skill_import_job_service.enqueue_commit(
        db, user_id=SYSTEM_USER_ID, request=request
    )
    background_tasks.add_task(
        skill_import_job_service.process_commit_job, result.job_id
    )
    return Response.success(data=result, message="System skill import queued")


@router.get(
    "/skills/import/jobs/{job_id}",
    response_model=ResponseSchema[SkillImportJobResponse],
)
def get_system_skill_import_job(
    job_id: "uuid.UUID",
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = skill_import_job_service.get_job(db, user_id=SYSTEM_USER_ID, job_id=job_id)
    return Response.success(data=result, message="System skill import job retrieved")


@router.get("/mcp-servers", response_model=ResponseSchema[list[McpServerAdminResponse]])
async def list_system_mcp_servers(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = mcp_server_service.list_servers_for_admin(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System MCP servers retrieved")


@router.post("/mcp-servers", response_model=ResponseSchema[McpServerAdminResponse])
async def create_system_mcp_server(
    request: McpServerCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    payload = request.model_copy(update={"scope": "system"})
    created_result = mcp_server_service.create_server(
        db, user_id=SYSTEM_USER_ID, request=payload
    )
    result = mcp_server_service.list_servers_for_admin(db, user_id=SYSTEM_USER_ID)
    created = next((item for item in result if item.id == created_result.id), None)
    if created is None:
        raise RuntimeError("Failed to load created system MCP server")
    return Response.success(data=created, message="System MCP server created")


@router.patch(
    "/mcp-servers/{server_id}", response_model=ResponseSchema[McpServerAdminResponse]
)
async def update_system_mcp_server(
    server_id: int,
    request: McpServerUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    mcp_server_service.update_server(
        db, user_id=SYSTEM_USER_ID, server_id=server_id, request=request
    )
    result = mcp_server_service.list_servers_for_admin(db, user_id=SYSTEM_USER_ID)
    updated = next((item for item in result if item.id == server_id), None)
    if updated is None:
        raise RuntimeError("Failed to load updated system MCP server")
    return Response.success(data=updated, message="System MCP server updated")


@router.delete("/mcp-servers/{server_id}", response_model=ResponseSchema[dict])
async def delete_system_mcp_server(
    server_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    mcp_server_service.delete_server(db, user_id=SYSTEM_USER_ID, server_id=server_id)
    return Response.success(data={"id": server_id}, message="System MCP server deleted")


@router.get("/plugins", response_model=ResponseSchema[list[PluginAdminResponse]])
async def list_system_plugins(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = plugin_service.list_plugins_for_admin(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System plugins retrieved")


@router.post("/plugins", response_model=ResponseSchema[PluginAdminResponse])
async def create_system_plugin(
    request: PluginCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    payload = request.model_copy(update={"scope": "system"})
    created_result = plugin_service.create_plugin(
        db, user_id=SYSTEM_USER_ID, request=payload
    )
    result = plugin_service.list_plugins_for_admin(db, user_id=SYSTEM_USER_ID)
    created = next((item for item in result if item.id == created_result.id), None)
    if created is None:
        raise RuntimeError("Failed to load created system plugin")
    return Response.success(data=created, message="System plugin created")


@router.patch(
    "/plugins/{plugin_id}", response_model=ResponseSchema[PluginAdminResponse]
)
async def update_system_plugin(
    plugin_id: int,
    request: PluginUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    plugin_service.update_plugin(
        db, user_id=SYSTEM_USER_ID, plugin_id=plugin_id, request=request
    )
    result = plugin_service.list_plugins_for_admin(db, user_id=SYSTEM_USER_ID)
    updated = next((item for item in result if item.id == plugin_id), None)
    if updated is None:
        raise RuntimeError("Failed to load updated system plugin")
    return Response.success(data=updated, message="System plugin updated")


@router.delete("/plugins/{plugin_id}", response_model=ResponseSchema[dict])
async def delete_system_plugin(
    plugin_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    plugin_service.delete_plugin(db, user_id=SYSTEM_USER_ID, plugin_id=plugin_id)
    return Response.success(data={"id": plugin_id}, message="System plugin deleted")


@router.post(
    "/plugins/import/discover",
    response_model=ResponseSchema[PluginImportDiscoverResponse],
)
def discover_system_plugin_import(
    file: UploadFile | None = File(default=None),
    github_url: str | None = Form(default=None),
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = plugin_import_service.discover(
        db,
        user_id=SYSTEM_USER_ID,
        file=file,
        github_url=github_url,
    )
    return Response.success(data=result, message="System plugin import discovered")


@router.post(
    "/plugins/import/commit",
    response_model=ResponseSchema[PluginImportCommitEnqueueResponse],
)
def commit_system_plugin_import(
    request: PluginImportCommitRequest,
    background_tasks: BackgroundTasks,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = plugin_import_job_service.enqueue_commit(
        db, user_id=SYSTEM_USER_ID, request=request
    )
    background_tasks.add_task(
        plugin_import_job_service.process_commit_job, result.job_id
    )
    return Response.success(data=result, message="System plugin import queued")


@router.get(
    "/plugins/import/jobs/{job_id}",
    response_model=ResponseSchema[PluginImportJobResponse],
)
def get_system_plugin_import_job(
    job_id: uuid.UUID,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = plugin_import_job_service.get_job(
        db, user_id=SYSTEM_USER_ID, job_id=job_id
    )
    return Response.success(data=result, message="System plugin import job retrieved")


@router.get(
    "/slash-commands", response_model=ResponseSchema[list[SlashCommandAdminResponse]]
)
async def list_system_slash_commands(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = slash_command_service.list_commands_for_admin(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System slash commands retrieved")


@router.post(
    "/slash-commands", response_model=ResponseSchema[SlashCommandAdminResponse]
)
async def create_system_slash_command(
    request: SlashCommandCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    created_result = slash_command_service.create_command(
        db, user_id=SYSTEM_USER_ID, request=request
    )
    result = slash_command_service.list_commands_for_admin(db, user_id=SYSTEM_USER_ID)
    created = next((item for item in result if item.id == created_result.id), None)
    if created is None:
        raise RuntimeError("Failed to load created system slash command")
    return Response.success(data=created, message="System slash command created")


@router.patch(
    "/slash-commands/{command_id}",
    response_model=ResponseSchema[SlashCommandAdminResponse],
)
async def update_system_slash_command(
    command_id: int,
    request: SlashCommandUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    slash_command_service.update_command(
        db, user_id=SYSTEM_USER_ID, command_id=command_id, request=request
    )
    result = slash_command_service.list_commands_for_admin(db, user_id=SYSTEM_USER_ID)
    updated = next((item for item in result if item.id == command_id), None)
    if updated is None:
        raise RuntimeError("Failed to load updated system slash command")
    return Response.success(data=updated, message="System slash command updated")


@router.delete("/slash-commands/{command_id}", response_model=ResponseSchema[dict])
async def delete_system_slash_command(
    command_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    slash_command_service.delete_command(
        db, user_id=SYSTEM_USER_ID, command_id=command_id
    )
    return Response.success(
        data={"id": command_id}, message="System slash command deleted"
    )


@router.get("/claude-md", response_model=ResponseSchema[ClaudeMdResponse])
async def get_system_claude_md(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = claude_md_service.get_settings(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System CLAUDE.md retrieved")


@router.put("/claude-md", response_model=ResponseSchema[ClaudeMdResponse])
async def upsert_system_claude_md(
    request: ClaudeMdAdminUpsertRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = claude_md_service.upsert_settings(
        db,
        user_id=SYSTEM_USER_ID,
        request=ClaudeMdUpsertRequest(
            enabled=request.enabled,
            content=request.content,
        ),
    )
    return Response.success(data=result, message="System CLAUDE.md updated")


@router.delete("/claude-md", response_model=ResponseSchema[dict])
async def delete_system_claude_md(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    claude_md_service.delete_settings(db, user_id=SYSTEM_USER_ID)
    return Response.success(data={"deleted": True}, message="System CLAUDE.md deleted")


@router.get("/subagents", response_model=ResponseSchema[list[SubAgentAdminResponse]])
async def list_system_subagents(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = sub_agent_service.list_subagents_for_admin(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System subagents retrieved")


@router.post("/subagents", response_model=ResponseSchema[SubAgentAdminResponse])
async def create_system_subagent(
    request: SubAgentCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    created_result = sub_agent_service.create_subagent(
        db, user_id=SYSTEM_USER_ID, request=request
    )
    result = sub_agent_service.list_subagents_for_admin(db, user_id=SYSTEM_USER_ID)
    created = next((item for item in result if item.id == created_result.id), None)
    if created is None:
        raise RuntimeError("Failed to load created system subagent")
    return Response.success(data=created, message="System subagent created")


@router.patch(
    "/subagents/{subagent_id}",
    response_model=ResponseSchema[SubAgentAdminResponse],
)
async def update_system_subagent(
    subagent_id: int,
    request: SubAgentUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    sub_agent_service.update_subagent(
        db,
        user_id=SYSTEM_USER_ID,
        subagent_id=subagent_id,
        request=request,
    )
    result = sub_agent_service.list_subagents_for_admin(db, user_id=SYSTEM_USER_ID)
    updated = next((item for item in result if item.id == subagent_id), None)
    if updated is None:
        raise RuntimeError("Failed to load updated system subagent")
    return Response.success(data=updated, message="System subagent updated")


@router.delete("/subagents/{subagent_id}", response_model=ResponseSchema[dict])
async def delete_system_subagent(
    subagent_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    sub_agent_service.delete_subagent(
        db, user_id=SYSTEM_USER_ID, subagent_id=subagent_id
    )
    return Response.success(data={"id": subagent_id}, message="System subagent deleted")


@router.get("/preset-visuals", response_model=ResponseSchema[list[PresetVisualSummary]])
async def list_preset_visuals_for_admin(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = preset_service.list_preset_visuals(db)
    return Response.success(data=result, message="Preset visuals retrieved")


@router.get("/presets", response_model=ResponseSchema[list[PresetAdminResponse]])
async def list_system_presets(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = preset_service.list_presets_for_admin(db, user_id=SYSTEM_USER_ID)
    return Response.success(data=result, message="System presets retrieved")


@router.post("/presets", response_model=ResponseSchema[PresetResponse])
async def create_system_preset(
    request: PresetCreateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = preset_service.create_preset(db, user_id=SYSTEM_USER_ID, request=request)
    return Response.success(data=result, message="System preset created")


@router.put("/presets/{preset_id}", response_model=ResponseSchema[PresetResponse])
async def update_system_preset(
    preset_id: int,
    request: PresetUpdateRequest,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = preset_service.update_preset(
        db,
        user_id=SYSTEM_USER_ID,
        preset_id=preset_id,
        request=request,
    )
    return Response.success(data=result, message="System preset updated")


@router.delete("/presets/{preset_id}", response_model=ResponseSchema[dict])
async def delete_system_preset(
    preset_id: int,
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    preset_service.delete_preset(db, user_id=SYSTEM_USER_ID, preset_id=preset_id)
    return Response.success(data={"id": preset_id}, message="System preset deleted")


@router.get("/users", response_model=ResponseSchema[list[CurrentUserResponse]])
async def list_users(
    _: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = user_admin_service.list_users(db)
    return Response.success(data=result, message="Users retrieved")


@router.patch(
    "/users/{user_id}/system-role", response_model=ResponseSchema[CurrentUserResponse]
)
async def update_user_system_role(
    user_id: str,
    request: SystemRoleUpdateRequest,
    current_user: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = user_admin_service.update_system_role(
        db,
        target_user_id=user_id,
        system_role=request.system_role,
        actor_user_id=current_user.id,
    )
    return Response.success(data=result, message="User system role updated")
