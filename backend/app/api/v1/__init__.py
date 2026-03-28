from fastapi import APIRouter

from app.api.v1 import (
    attachments,
    audio,
    callback,
    capability_recommendations,
    claude_md,
    deliverables,
    env_vars,
    models,
    internal_claude_md,
    internal_env_vars,
    internal_memories,
    internal_tasks,
    internal_skills,
    im,
    internal_plugin_config,
    internal_slash_commands,
    internal_mcp_config,
    internal_scheduled_tasks,
    internal_skill_config,
    internal_subagents,
    internal_user_input_requests,
    memories,
    mcp_servers,
    messages,
    plugin_imports,
    plugin_installs,
    plugins,
    pending_skill_creations,
    projects,
    runs,
    schedules,
    search,
    scheduled_tasks,
    session_queue,
    sessions,
    skill_marketplace,
    slash_commands,
    skill_installs,
    skill_imports,
    skills,
    subagents,
    tasks,
    tool_executions,
    usage,
    user_input_requests,
    user_mcp_installs,
)
from app.core.settings import get_settings
from app.schemas.response import Response

api_v1_router = APIRouter()
api_v1_router.include_router(sessions.router)
api_v1_router.include_router(session_queue.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(schedules.router)
api_v1_router.include_router(callback.router)
api_v1_router.include_router(deliverables.router)
api_v1_router.include_router(messages.router)
api_v1_router.include_router(memories.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(tool_executions.router)
api_v1_router.include_router(usage.router)
api_v1_router.include_router(attachments.router)
api_v1_router.include_router(audio.router)
api_v1_router.include_router(capability_recommendations.router)
api_v1_router.include_router(env_vars.router)
api_v1_router.include_router(claude_md.router)
api_v1_router.include_router(models.router)
api_v1_router.include_router(search.router)
api_v1_router.include_router(im.router)
api_v1_router.include_router(internal_claude_md.router)
api_v1_router.include_router(internal_env_vars.router)
api_v1_router.include_router(internal_memories.router)
api_v1_router.include_router(internal_tasks.router)
api_v1_router.include_router(internal_skills.router)
api_v1_router.include_router(internal_mcp_config.router)
api_v1_router.include_router(internal_skill_config.router)
api_v1_router.include_router(internal_scheduled_tasks.router)
api_v1_router.include_router(internal_user_input_requests.router)
api_v1_router.include_router(internal_slash_commands.router)
api_v1_router.include_router(internal_subagents.router)
api_v1_router.include_router(internal_plugin_config.router)
api_v1_router.include_router(mcp_servers.router)
api_v1_router.include_router(user_mcp_installs.router)
api_v1_router.include_router(skills.router)
api_v1_router.include_router(skill_marketplace.router)
api_v1_router.include_router(skill_imports.router)
api_v1_router.include_router(skill_installs.router)
api_v1_router.include_router(pending_skill_creations.router)
api_v1_router.include_router(plugins.router)
api_v1_router.include_router(plugin_imports.router)
api_v1_router.include_router(plugin_installs.router)
api_v1_router.include_router(slash_commands.router)
api_v1_router.include_router(subagents.router)
api_v1_router.include_router(user_input_requests.router)
api_v1_router.include_router(scheduled_tasks.router)


@api_v1_router.get("/")
async def root():
    settings = get_settings()
    return Response.success(
        data={
            "service": settings.app_name,
            "status": "running",
            "version": settings.app_version,
        }
    )


@api_v1_router.get("/health")
async def health():
    settings = get_settings()
    return Response.success(
        data={
            "service": settings.app_name,
            "status": "healthy",
        }
    )
