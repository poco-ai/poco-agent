/**
 * Session-related API types matching backend schemas
 */

import type { ApiStatePatch } from "./callback";

export interface SessionCreateRequest {
  config?: TaskConfig | null;
}

export interface SessionUpdateRequest {
  status?: string | null;
  sdk_session_id?: string | null;
  title?: string | null;
  workspace_archive_url?: string | null;
  state_patch?: ApiStatePatch | null;
  workspace_files_prefix?: string | null;
  workspace_manifest_key?: string | null;
  workspace_archive_key?: string | null;
  workspace_export_status?: string | null;
  project_id?: string | null;
}

export interface SessionCancelRequest {
  reason?: string | null;
}

export interface SessionCancelResponse {
  session_id: string;
  status: string;
  canceled_runs: number;
  expired_user_input_requests: number;
  executor_cancelled: boolean;
}

export interface SessionBranchRequest {
  message_id: number;
}

export interface SessionRegenerateRequest {
  user_message_id: number;
  assistant_message_id: number;
}

export interface SessionEditMessageRequest {
  user_message_id: number;
  content: string;
}

export interface SessionBranchResponse {
  session_id: string;
  source_session_id: string;
  cutoff_message_id: number;
}

export interface SessionResponse {
  session_id: string; // UUID
  user_id: string;
  sdk_session_id: string | null;
  project_id?: string | null;
  title?: string | null;
  config_snapshot: Record<string, unknown> | null;
  workspace_archive_url: string | null;
  state_patch?: ApiStatePatch | null;
  workspace_export_status?: string | null;
  workspace_files_prefix?: string | null;
  workspace_manifest_key?: string | null;
  workspace_archive_key?: string | null;
  status: string;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface SessionStateResponse {
  session_id: string;
  status: string;
  state_patch?: ApiStatePatch | null;
  workspace_export_status?: string | null;
  updated_at: string;
}

export interface MessageResponse {
  id: number;
  role: string;
  content: Record<string, unknown>;
  text_preview?: string | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

export interface MessageAttachmentsResponse {
  message_id: number;
  attachments: InputFile[];
}

export interface ToolExecutionResponse {
  id: string; // UUID
  message_id: number | null;
  tool_use_id: string | null;
  tool_name: string;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  is_error: boolean;
  duration_ms: number | null;
  created_at: string; // ISO datetime
}

export interface UsageResponse {
  total_cost_usd: number | null;
  total_duration_ms: number | null;
  usage_json: Record<string, unknown> | null;
}

export interface InputFile {
  [x: string]: unknown;
  id?: string | null;
  type?: string;
  name: string;
  source: string;
  size?: number | null;
  content_type?: string | null;
  path?: string | null;
  url?: string | null;
}

export interface TaskConfig {
  repo_url?: string | null;
  git_branch?: string; // defaults to "main"
  /** Env var key holding a GitHub token (e.g. "GITHUB_TOKEN"). */
  git_token_env_key?: string | null;
  /** Optional explicit model override for this session/run. */
  model?: string | null;
  /** Built-in browser capability toggle (Playwright MCP is injected internally). */
  browser_enabled?: boolean;
  /** MCP server enable/disable toggles (true=enabled, false=disabled).
   *  Servers not in this object use their default enabled state from user installations.
   */
  mcp_config?: Record<string, boolean>;
  /** Skill enable/disable toggles (true=enabled, false=disabled).
   *  Skills not in this object use their default enabled state from user installs.
   */
  skill_config?: Record<string, boolean>;
  /** Plugin enable/disable toggles (true=enabled, false=disabled).
   *  Plugins not in this object use their default enabled state from user installs.
   */
  plugin_config?: Record<string, boolean>;
  /** Optional explicit subagent selection (by id). */
  subagent_ids?: number[];
  input_files?: InputFile[];
}
