import type { AddTaskOptions } from "@/features/projects/types";
import type { InputFile } from "@/features/chat/types/api/session";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";
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
  memory_enabled?: boolean | null;
  mcp_config?: Record<string, boolean> | null;
  skill_config?: Record<string, boolean> | null;
  plugin_config?: Record<string, boolean> | null;
  workspace_strategy?:
    | "clone"
    | "worktree"
    | "sparse-clone"
    | "sparse-worktree"
    | null;
  workspace_sparse_paths?: string[] | null;
  workspace_reference_branch?: string | null;
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
  selectedModel?: ModelSelection | null;
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
