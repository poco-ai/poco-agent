export type PendingSkillCreationStatus =
  | "pending"
  | "creating"
  | "success"
  | "failed"
  | "canceled";

export interface PendingSkillCreation {
  id: string;
  session_id: string;
  tool_use_id?: string | null;
  detected_name: string;
  resolved_name?: string | null;
  description?: string | null;
  workspace_files_prefix?: string | null;
  skill_relative_path: string;
  status: PendingSkillCreationStatus;
  skill_id?: number | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PendingSkillCreationConfirmInput {
  resolved_name?: string | null;
  description?: string | null;
  overwrite?: boolean;
}

export interface PendingSkillCreationCancelInput {
  reason?: string | null;
}
