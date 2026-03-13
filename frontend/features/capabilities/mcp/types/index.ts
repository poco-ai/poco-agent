import type { SourceInfo } from "@/features/capabilities/types/source";

export interface McpServer {
  id: number;
  name: string;
  description: string | null;
  source?: SourceInfo | null;
  scope: string;
  owner_user_id: string | null;
  server_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface McpServerCreateInput {
  name: string;
  description?: string | null;
  server_config: Record<string, unknown>;
  scope?: string | null;
}

export interface McpServerUpdateInput {
  name?: string | null;
  description?: string | null;
  server_config?: Record<string, unknown> | null;
  scope?: string | null;
}

export interface UserMcpInstall {
  id: number;
  user_id: string;
  server_id: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserMcpInstallCreateInput {
  server_id: number;
  enabled?: boolean;
}

export interface UserMcpInstallUpdateInput {
  enabled?: boolean | null;
}

export interface McpInstallBulkUpdateInput {
  enabled: boolean;
  install_ids?: number[] | null;
}

export interface McpInstallBulkUpdateResponse {
  updated_count: number;
}
