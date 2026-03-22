/**
 * File/Workspace-related API types matching backend schemas
 */

export interface FileNode {
  id: string;
  name: string;
  type: "file" | "folder";
  path: string;
  children?: FileNode[] | null;
  url?: string | null;
  mimeType?: string | null;
  oss_status?: string | null;
  oss_meta?: Record<string, unknown> | null;
}

export interface WorkspaceArchiveResponse {
  url?: string | null;
  filename: string;
}

export interface SubmitSkillResponse {
  pending_id: string;
  status: string;
}
