import { createSessionAction } from "@/features/chat/actions/session-actions";
import type { TaskConfig } from "@/features/chat/types/api/session";
import { scheduledTasksService } from "@/features/scheduled-tasks/api/scheduled-tasks-api";
import type {
  TaskSubmitContext,
  TaskSubmitInput,
  TaskSubmitResult,
} from "@/features/task-composer/types";

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
  const selectedModel = (input.selectedModel || "").trim();

  if (selectedModel) {
    config.model = selectedModel;
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
  if (options.browser_enabled) {
    config.browser_enabled = true;
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
