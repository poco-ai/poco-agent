export type WorkspaceIssueStatus = "todo" | "in_progress" | "done" | "canceled";

export interface AgentAssignmentRuntimeSummary {
  persistent_runtime_id: string;
  runtime_key: string;
  owner_type: string;
  owner_id: string;
  agent_identity_id?: string | null;
  assignment_id?: string | null;
  session_id?: string | null;
  container_id?: string | null;
  lifecycle_state: string;
  auto_resume: boolean;
  idle_timeout_seconds: number;
  warm_retention_seconds: number;
  keepalive_until?: string | null;
  last_activity_at?: string | null;
  last_started_at?: string | null;
  last_stopped_at?: string | null;
  last_stop_reason?: string | null;
  worker_id?: string | null;
  browser_enabled: boolean;
  filesystem_fingerprint?: string | null;
}

export interface WorkspaceBoardInput {
  name: string;
  description?: string | null;
}

export interface WorkspaceBoard {
  board_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  created_by: string;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceIssue {
  issue_id: string;
  workspace_id: string;
  board_id: string;
  title: string;
  description?: string | null;
  status: WorkspaceIssueStatus;
  position: number;
  type: string;
  priority: string;
  due_date?: string | null;
  assignee_user_id?: string | null;
  assignee_preset_id?: number | null;
  reporter_user_id?: string | null;
  related_project_id?: string | null;
  creator_user_id: string;
  updated_by?: string | null;
  agent_assignment?: AgentAssignment | null;
  created_at: string;
  updated_at: string;
}

export interface AgentAssignment {
  assignment_id: string;
  workspace_id: string;
  issue_id: string;
  preset_id: number;
  trigger_mode: "persistent_sandbox" | "scheduled_task";
  session_id?: string | null;
  container_id?: string | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  prompt: string;
  schedule_cron?: string | null;
  last_triggered_at?: string | null;
  last_completed_at?: string | null;
  runtime_summary?: AgentAssignmentRuntimeSummary | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AgentAssignmentActionResult {
  assignment: AgentAssignment;
  issue_status: string;
}

export interface WorkspaceIssueMoveInput {
  status: WorkspaceIssueStatus;
  position: number;
}
