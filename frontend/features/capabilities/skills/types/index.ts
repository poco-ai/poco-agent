import type { SourceInfo } from "@/features/capabilities/types/source";

export interface Skill {
  id: number;
  name: string;
  description: string | null;
  entry: Record<string, unknown>;
  source?: SourceInfo | null;
  scope: string;
  owner_user_id: string | null;
  default_enabled: boolean;
  force_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillCreateInput {
  name: string;
  entry: Record<string, unknown>;
  description?: string | null;
  scope?: string | null;
  default_enabled?: boolean | null;
  force_enabled?: boolean | null;
}

export interface SkillUpdateInput {
  name?: string | null;
  entry?: Record<string, unknown> | null;
  description?: string | null;
  scope?: string | null;
  default_enabled?: boolean | null;
  force_enabled?: boolean | null;
}

export interface UserSkillInstall {
  id: number;
  user_id: string;
  skill_id: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillInstallCreateInput {
  skill_id: number;
  enabled?: boolean;
}

export interface SkillInstallUpdateInput {
  enabled?: boolean | null;
}

export interface SkillInstallBulkUpdateInput {
  enabled: boolean;
  install_ids?: number[] | null;
}

export interface SkillInstallBulkUpdateResponse {
  updated_count: number;
}

export interface SkillImportCandidate {
  relative_path: string;
  skill_name: string | null;
  requires_name: boolean;
  will_overwrite: boolean;
}

export interface SkillImportDiscoverResponse {
  archive_key: string;
  candidates: SkillImportCandidate[];
  preselected_relative_path?: string | null;
  skillsmp_item?: SkillsMpSkillItem | null;
}

export interface SkillImportSelection {
  relative_path: string;
  name_override?: string | null;
}

export interface SkillImportCommitInput {
  archive_key: string;
  selections: SkillImportSelection[];
}

export interface SkillImportResultItem {
  relative_path: string;
  skill_name: string | null;
  skill_id: number | null;
  overwritten: boolean;
  status: string;
  error: string | null;
}

export interface SkillImportCommitResponse {
  items: SkillImportResultItem[];
}

export interface SkillImportCommitEnqueueResponse {
  job_id: string;
  status: string;
}

export interface SkillImportJobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  result: SkillImportCommitResponse | null;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface SkillsMpSkillItem {
  external_id: string;
  name: string;
  description: string | null;
  author: string | null;
  author_avatar_url: string | null;
  github_url: string | null;
  branch: string | null;
  relative_skill_path: string | null;
  stars: number;
  forks: number;
  updated_at: string | null;
  skillsmp_url: string;
  tags: string[];
}

export interface SkillsMpSearchResponse {
  items: SkillsMpSkillItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
}

export interface SkillsMpRecommendationSection {
  key: string;
  title: string;
  items: SkillsMpSkillItem[];
}

export interface SkillsMpRecommendationsResponse {
  sections: SkillsMpRecommendationSection[];
}

export interface SkillsMpMarketplaceStatusResponse {
  configured: boolean;
}

export interface SkillsMpImportDiscoverInput {
  item: SkillsMpSkillItem;
}

export interface SkillImportApi {
  discover: (formData: FormData) => Promise<SkillImportDiscoverResponse>;
  commit: (
    input: SkillImportCommitInput,
  ) => Promise<SkillImportCommitEnqueueResponse>;
  getJob: (jobId: string) => Promise<SkillImportJobStatusResponse>;
}

export interface SkillImportServiceLike {
  importDiscover?: (formData: FormData) => Promise<SkillImportDiscoverResponse>;
  importCommit?: (
    input: SkillImportCommitInput,
  ) => Promise<SkillImportCommitEnqueueResponse>;
  getImportJob?: (jobId: string) => Promise<SkillImportJobStatusResponse>;
}
