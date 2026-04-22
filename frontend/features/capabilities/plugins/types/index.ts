import type { SourceInfo } from "@/features/capabilities/types/source";

export interface Plugin {
  id: number;
  name: string;
  entry: Record<string, unknown>;
  source?: SourceInfo | null;
  scope: string;
  owner_user_id: string | null;
  default_enabled: boolean;
  force_enabled: boolean;
  description: string | null;
  version: string | null;
  manifest: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PluginCreateInput {
  name: string;
  entry: Record<string, unknown>;
  scope?: string | null;
  description?: string | null;
  version?: string | null;
  manifest?: Record<string, unknown> | null;
  default_enabled?: boolean | null;
  force_enabled?: boolean | null;
}

export interface PluginUpdateInput {
  name?: string | null;
  entry?: Record<string, unknown> | null;
  scope?: string | null;
  description?: string | null;
  version?: string | null;
  manifest?: Record<string, unknown> | null;
  default_enabled?: boolean | null;
  force_enabled?: boolean | null;
}

export interface UserPluginInstall {
  id: number;
  user_id: string;
  plugin_id: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PluginInstallCreateInput {
  plugin_id: number;
  enabled?: boolean;
}

export interface PluginInstallUpdateInput {
  enabled?: boolean | null;
}

export interface PluginInstallBulkUpdateInput {
  enabled: boolean;
  install_ids?: number[] | null;
}

export interface PluginInstallBulkUpdateResponse {
  updated_count: number;
}

export interface PluginImportCandidate {
  relative_path: string;
  plugin_name: string | null;
  version: string | null;
  description: string | null;
  requires_name: boolean;
  will_overwrite: boolean;
}

export interface PluginImportDiscoverResponse {
  archive_key: string;
  candidates: PluginImportCandidate[];
}

export interface PluginImportSelection {
  relative_path: string;
  name_override?: string | null;
}

export interface PluginImportCommitInput {
  archive_key: string;
  selections: PluginImportSelection[];
}

export interface PluginImportResultItem {
  relative_path: string;
  plugin_name: string | null;
  plugin_id: number | null;
  overwritten: boolean;
  status: string;
  error: string | null;
}

export interface PluginImportCommitResponse {
  items: PluginImportResultItem[];
}

export interface PluginImportCommitEnqueueResponse {
  job_id: string;
  status: string;
}

export interface PluginImportJobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  result: PluginImportCommitResponse | null;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface PluginImportApi {
  discover: (formData: FormData) => Promise<PluginImportDiscoverResponse>;
  commit: (
    input: PluginImportCommitInput,
  ) => Promise<PluginImportCommitEnqueueResponse>;
  getJob: (jobId: string) => Promise<PluginImportJobStatusResponse>;
}

export interface PluginImportServiceLike {
  importDiscover?: (
    formData: FormData,
  ) => Promise<PluginImportDiscoverResponse>;
  importCommit?: (
    input: PluginImportCommitInput,
  ) => Promise<PluginImportCommitEnqueueResponse>;
  getImportJob?: (jobId: string) => Promise<PluginImportJobStatusResponse>;
}
