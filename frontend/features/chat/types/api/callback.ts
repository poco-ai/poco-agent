/**
 * Callback-related API types matching backend schemas
 */

export type CallbackStatus = "accepted" | "running" | "completed" | "failed";

export interface TodoItem {
  content: string;
  status: string;
  active_form?: string | null;
}

export interface McpStatus {
  server_name: string;
  status: string;
  message?: string | null;
}

// Type alias for backward compatibility
export type McpStatusItem = McpStatus;

export type FileChangeStatus = "added" | "modified" | "deleted" | "renamed";

export interface FileChange {
  path: string;
  status: FileChangeStatus | string;
  added_lines?: number;
  deleted_lines?: number;
  diff?: string | null;
  old_path?: string | null;
}

export interface WorkspaceState {
  repository?: string | null;
  branch?: string | null;
  total_added_lines?: number;
  total_deleted_lines?: number;
  file_change_count?: number;
  file_changes?: FileChange[];
  last_change: string; // ISO datetime
}

export interface BrowserState {
  enabled: boolean;
}

export interface AgentCurrentState {
  todos?: TodoItem[];
  mcp_status?: McpStatus[];
  browser?: BrowserState | null;
  workspace_state?: WorkspaceState | null;
  current_step?: string | null;
}

/**
 * State patch for incremental session updates
 * Contains agent execution state that can be merged into session state
 */
export interface ApiStatePatch {
  todos?: TodoItem[];
  mcp_status?: McpStatus[];
  browser?: BrowserState | null;
  workspace_state?: WorkspaceState | null;
  current_step?: string | null;
}

export interface AgentCallbackRequest {
  session_id: string;
  time: string; // ISO datetime
  status: CallbackStatus;
  progress: number;
  new_message?: unknown | null;
  state_patch?: ApiStatePatch | null;
  sdk_session_id?: string | null;
}

export interface CallbackResponse {
  session_id: string;
  status: string;
  callback_status?: CallbackStatus | null;
  message?: string | null;
}
