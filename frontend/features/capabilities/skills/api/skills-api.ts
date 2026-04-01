import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import { markSlashCommandSuggestionsInvalidated } from "@/features/capabilities/slash-commands/api/suggestions-state";
import type { FileNode } from "@/features/chat";
import type {
  SkillInstallCreateInput,
  SkillInstallUpdateInput,
  SkillInstallBulkUpdateInput,
  SkillInstallBulkUpdateResponse,
  Skill,
  SkillCreateInput,
  SkillUpdateInput,
  UserSkillInstall,
  SkillImportDiscoverResponse,
  SkillImportCommitInput,
  SkillImportCommitEnqueueResponse,
  SkillImportJobStatusResponse,
  SkillManifestValidationResponse,
  SkillsMpImportDiscoverInput,
  SkillsMpMarketplaceStatusResponse,
  SkillsMpRecommendationsResponse,
  SkillsMpSearchResponse,
} from "@/features/capabilities/skills/types";

function buildQuery(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    searchParams.set(key, String(value));
  }
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

function emitSlashCommandSuggestionsInvalidated(): void {
  markSlashCommandSuggestionsInvalidated();
}

export const skillsService = {
  listSkills: async (options?: { revalidate?: number }): Promise<Skill[]> => {
    return apiClient.get<Skill[]>(API_ENDPOINTS.skills, {
      next: { revalidate: options?.revalidate },
    });
  },

  getSkill: async (
    skillId: number,
    options?: { revalidate?: number },
  ): Promise<Skill> => {
    return apiClient.get<Skill>(API_ENDPOINTS.skill(skillId), {
      next: { revalidate: options?.revalidate },
    });
  },

  listSkillFiles: async (
    skillId: number,
    options?: { revalidate?: number },
  ): Promise<FileNode[]> => {
    return apiClient.get<FileNode[]>(API_ENDPOINTS.skillFiles(skillId), {
      cache: "no-store",
      next: { revalidate: options?.revalidate },
    });
  },

  createSkill: async (input: SkillCreateInput): Promise<Skill> => {
    const created = await apiClient.post<Skill>(API_ENDPOINTS.skills, input);
    emitSlashCommandSuggestionsInvalidated();
    return created;
  },

  updateSkill: async (
    skillId: number,
    input: SkillUpdateInput,
  ): Promise<Skill> => {
    const updated = await apiClient.patch<Skill>(
      API_ENDPOINTS.skill(skillId),
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return updated;
  },

  deleteSkill: async (skillId: number): Promise<Record<string, unknown>> => {
    const removed = await apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.skill(skillId),
    );
    emitSlashCommandSuggestionsInvalidated();
    return removed;
  },

  validateManifest: async (
    skillId: number,
  ): Promise<SkillManifestValidationResponse> => {
    return apiClient.post<SkillManifestValidationResponse>(
      API_ENDPOINTS.skillManifestValidate(skillId),
      {},
    );
  },

  listInstalls: async (options?: {
    revalidate?: number;
  }): Promise<UserSkillInstall[]> => {
    return apiClient.get<UserSkillInstall[]>(API_ENDPOINTS.skillInstalls, {
      next: { revalidate: options?.revalidate },
    });
  },

  createInstall: async (
    input: SkillInstallCreateInput,
  ): Promise<UserSkillInstall> => {
    const created = await apiClient.post<UserSkillInstall>(
      API_ENDPOINTS.skillInstalls,
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return created;
  },

  updateInstall: async (
    installId: number,
    input: SkillInstallUpdateInput,
  ): Promise<UserSkillInstall> => {
    const updated = await apiClient.patch<UserSkillInstall>(
      API_ENDPOINTS.skillInstall(installId),
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return updated;
  },

  bulkUpdateInstalls: async (
    input: SkillInstallBulkUpdateInput,
  ): Promise<SkillInstallBulkUpdateResponse> => {
    const updated = await apiClient.patch<SkillInstallBulkUpdateResponse>(
      API_ENDPOINTS.skillInstallsBulk,
      input,
    );
    emitSlashCommandSuggestionsInvalidated();
    return updated;
  },

  deleteInstall: async (
    installId: number,
  ): Promise<Record<string, unknown>> => {
    const removed = await apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.skillInstall(installId),
    );
    emitSlashCommandSuggestionsInvalidated();
    return removed;
  },

  importDiscover: async (
    formData: FormData,
  ): Promise<SkillImportDiscoverResponse> => {
    return apiClient.post<SkillImportDiscoverResponse>(
      API_ENDPOINTS.skillImportDiscover,
      formData,
      { timeoutMs: 5 * 60_000 },
    );
  },

  importCommit: async (
    input: SkillImportCommitInput,
  ): Promise<SkillImportCommitEnqueueResponse> => {
    return apiClient.post<SkillImportCommitEnqueueResponse>(
      API_ENDPOINTS.skillImportCommit,
      input,
    );
  },

  getImportJob: async (
    jobId: string,
  ): Promise<SkillImportJobStatusResponse> => {
    return apiClient.get<SkillImportJobStatusResponse>(
      API_ENDPOINTS.skillImportJob(jobId),
      { cache: "no-store" },
    );
  },

  getMarketplaceStatus:
    async (): Promise<SkillsMpMarketplaceStatusResponse> => {
      return apiClient.get<SkillsMpMarketplaceStatusResponse>(
        API_ENDPOINTS.skillsMarketplaceStatus,
        { cache: "no-store" },
      );
    },

  searchMarketplaceSkills: async (params: {
    q: string;
    page?: number;
    page_size?: number;
    semantic?: boolean;
  }): Promise<SkillsMpSearchResponse> => {
    return apiClient.get<SkillsMpSearchResponse>(
      `${API_ENDPOINTS.skillsMarketplaceSearch}${buildQuery(params)}`,
      { cache: "no-store" },
    );
  },

  listMarketplaceRecommendations: async (params?: {
    limit?: number;
  }): Promise<SkillsMpRecommendationsResponse> => {
    return apiClient.get<SkillsMpRecommendationsResponse>(
      `${API_ENDPOINTS.skillsMarketplaceRecommendations}${buildQuery(params ?? {})}`,
      { cache: "no-store" },
    );
  },

  marketplaceImportDiscover: async (
    input: SkillsMpImportDiscoverInput,
  ): Promise<SkillImportDiscoverResponse> => {
    return apiClient.post<SkillImportDiscoverResponse>(
      API_ENDPOINTS.skillsMarketplaceImportDiscover,
      input,
      { timeoutMs: 5 * 60_000 },
    );
  },

  // Backward-compatible alias used by server components
  list: async (options?: { revalidate?: number }) =>
    skillsService.listSkills(options),
};
