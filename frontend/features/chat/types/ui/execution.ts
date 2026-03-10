/**
 * Execution-related UI types (frontend-specific)
 */

import type { ApiStatePatch } from "../api/callback";

export type ExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "canceled";

export type ArtifactType =
  | "text"
  | "code_diff"
  | "image"
  | "ppt"
  | "pdf"
  | "markdown"
  | "json";

export interface Artifact {
  id: string;
  type: ArtifactType;
  title: string;
  content?: string;
  url?: string;
  metadata?: {
    language?: string;
    size?: number;
    format?: string;
  };
  created_at: string;
}

export interface SkillUse {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed";
  duration?: number;
  created_at: string;
}

export interface NewMessage {
  title: string;
}

/**
 * Configuration snapshot from session creation
 * Contains the IDs of MCP servers, skills, and presets used in this session
 */
export interface ConfigSnapshot {
  mcp_server_ids?: number[];
  skill_ids?: number[];
  plugin_ids?: number[];
  browser_enabled?: boolean;
  memory_enabled?: boolean;
  model?: string;
  model_provider_id?: string;
  repo_url?: string;
  git_branch?: string;
  git_token_env_key?: string | null;
}

/**
 * Frontend StatePatch extends API StatePatch with UI-specific fields
 */
export interface StatePatch extends ApiStatePatch {
  artifacts?: Artifact[];
  skills_used?: SkillUse[];
}

/**
 * Frontend aggregation of session execution state
 * Used for real-time UI updates during agent execution
 */
export interface ExecutionSession {
  session_id: string;
  time: string;
  status: ExecutionStatus;
  progress: number;
  new_message?: NewMessage;
  state_patch: StatePatch;
  config_snapshot?: ConfigSnapshot | null;
  task_name?: string;
  user_prompt?: string;
  title?: string | null;
}
