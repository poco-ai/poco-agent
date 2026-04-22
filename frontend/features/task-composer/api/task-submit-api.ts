import { createSessionAction } from "../../chat/actions/session-actions.ts";
import type { TaskConfig } from "../../chat/types/api/session.ts";
import { normalizeModelSelection } from "../../chat/lib/model-catalog.ts";
import { scheduledTasksService } from "../../scheduled-tasks/api/scheduled-tasks-api.ts";
import type {
  TaskSubmitContext,
  TaskSubmitInput,
  TaskSubmitResult,
} from "../types/index.ts";

const DEFAULT_BRANCH = "main";
const DEFAULT_CRON = "*/5 * * * *";
const DEFAULT_TIMEZONE = "UTC";

function buildTaskConfig(
  input: TaskSubmitInput,
): (TaskConfig & Record<string, unknown>) | undefined {
  const options = input.options ?? {};
  const config: TaskConfig & Record<string, unknown> = {};
  const inputFiles = options.attachments ?? [];
  const repoUrl = (options.repo_url || "").trim();
  const gitBranch = (options.git_branch || "").trim() || DEFAULT_BRANCH;
  const gitTokenEnvKey = (options.git_token_env_key || "").trim();
  const selectedModel = normalizeModelSelection(input.selectedModel);

  if (selectedModel.modelId) {
    config.model = selectedModel.modelId;
    if (selectedModel.providerId) {
      config.model_provider_id = selectedModel.providerId;
    }
  }
  if (inputFiles.length > 0) {
    config.input_files = inputFiles;
  }
  if (repoUrl) {
    config.repo_url = repoUrl;
    config.git_branch = gitBranch;
    if (gitTokenEnvKey) {
      config.git_token_env_key = gitTokenEnvKey;
    }
  }
  if (typeof options.preset_id === "number") {
    config.preset_id = options.preset_id;
  }
  if (typeof options.browser_enabled === "boolean") {
    config.browser_enabled = options.browser_enabled;
  }
  if (typeof options.memory_enabled === "boolean") {
    config.memory_enabled = options.memory_enabled;
  }
  if (options.mcp_config && Object.keys(options.mcp_config).length > 0) {
    config.mcp_config = options.mcp_config;
  }
  if (options.skill_config && Object.keys(options.skill_config).length > 0) {
    config.skill_config = options.skill_config;
  }
  if (options.plugin_config && Object.keys(options.plugin_config).length > 0) {
    config.plugin_config = options.plugin_config;
  }
  if (Array.isArray(options.subagent_ids)) {
    config.subagent_ids = options.subagent_ids;
  }
  if (options.filesystem_mode) {
    config.filesystem_mode = options.filesystem_mode;
  }
  if (Array.isArray(options.local_mounts)) {
    config.local_mounts = options.local_mounts;
  }

  return Object.keys(config).length > 0 ? config : undefined;
}

export async function submitScheduledTask(
  input: TaskSubmitInput,
): Promise<TaskSubmitResult> {
  const prompt = input.prompt;
  const options = input.options ?? {};
  const config = buildTaskConfig(input);
  const scheduledTask = options.scheduled_task;
  const name = (scheduledTask?.name || "").trim() || prompt.trim().slice(0, 32);
  const cron = (scheduledTask?.cron || "").trim() || DEFAULT_CRON;
  const timezone = (scheduledTask?.timezone || "").trim() || DEFAULT_TIMEZONE;
  const enabled = Boolean(scheduledTask?.enabled ?? true);
  const reuseSession = Boolean(scheduledTask?.reuse_session ?? true);

  const created = await scheduledTasksService.create({
    name,
    cron,
    timezone,
    prompt,
    enabled,
    reuse_session: reuseSession,
    project_id: input.projectId,
    config,
  });

  return {
    kind: "scheduled",
    scheduledTaskId: created.scheduled_task_id,
    projectId: input.projectId,
  };
}

export async function submitTask(
  input: TaskSubmitInput,
  context?: TaskSubmitContext,
): Promise<TaskSubmitResult> {
  const config = buildTaskConfig(input);
  const runSchedule = input.options?.run_schedule ?? null;
  const response = await createSessionAction({
    prompt: input.prompt,
    config,
    projectId: input.projectId,
    permission_mode: input.mode === "plan" ? "plan" : "default",
    schedule_mode: runSchedule?.schedule_mode,
    timezone: runSchedule?.timezone,
    scheduled_at: runSchedule?.scheduled_at,
  });

  if (typeof window !== "undefined") {
    window.localStorage.setItem(
      `session_prompt_${response.sessionId}`,
      input.prompt,
    );
  }

  if (context?.addTask) {
    context.addTask(input.prompt, {
      id: response.sessionId,
      timestamp: new Date().toISOString(),
      status: "running",
      projectId: input.projectId,
    });
  }

  return {
    kind: "session",
    sessionId: response.sessionId,
    runId: response.runId,
    status: response.status,
    projectId: input.projectId,
  };
}
