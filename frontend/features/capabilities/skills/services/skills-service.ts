import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import { SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT } from "@/features/capabilities/slash-commands/services/slash-commands-service";
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
} from "@/features/capabilities/skills/types";

function emitSlashCommandSuggestionsInvalidated(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT));
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

  // Backward-compatible alias used by server components
  list: async (options?: { revalidate?: number }) =>
    skillsService.listSkills(options),
};
