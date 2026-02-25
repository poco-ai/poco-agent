import type { AddTaskOptions } from "@/features/projects/types";
import type { InputFile } from "@/features/chat/types/api/session";
import type { RunScheduleMode } from "@/features/task-composer/model/run-schedule";

export type ComposerMode = "plan" | "task" | "scheduled";
export type RepoUsageMode = "session" | "create_project";

export interface TaskSendOptions {
  attachments?: InputFile[];
  repo_url?: string | null;
  git_branch?: string | null;
  git_token_env_key?: string | null;
  repo_usage?: RepoUsageMode | null;
  project_name?: string | null;
  browser_enabled?: boolean | null;
  run_schedule?: {
    schedule_mode: RunScheduleMode;
    timezone: string;
    scheduled_at: string | null;
  } | null;
  scheduled_task?: {
    name: string;
    cron: string;
    timezone: string;
    enabled: boolean;
    reuse_session: boolean;
  } | null;
}

export interface TaskSubmitInput {
  prompt: string;
  mode: ComposerMode;
  options?: TaskSendOptions;
  selectedModel?: string | null;
  projectId?: string;
}

export interface TaskSubmitContext {
  addTask?: (title: string, options?: AddTaskOptions) => unknown;
}

export interface TaskSubmitResult {
  kind: "session" | "scheduled";
  sessionId?: string;
  runId?: string;
  status?: string;
  scheduledTaskId?: string;
  projectId?: string;
}
