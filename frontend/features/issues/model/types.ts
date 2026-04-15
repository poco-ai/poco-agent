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
  status: string;
  type: string;
  priority: string;
  due_date?: string | null;
  assignee_user_id?: string | null;
  assignee_preset_id?: number | null;
  reporter_user_id?: string | null;
  related_project_id?: string | null;
  creator_user_id: string;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}
