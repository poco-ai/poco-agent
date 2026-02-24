import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  Plugin,
  PluginCreateInput,
  PluginUpdateInput,
  UserPluginInstall,
  PluginInstallCreateInput,
  PluginInstallUpdateInput,
  PluginInstallBulkUpdateInput,
  PluginInstallBulkUpdateResponse,
  PluginImportDiscoverResponse,
  PluginImportCommitInput,
  PluginImportCommitEnqueueResponse,
  PluginImportJobStatusResponse,
} from "@/features/capabilities/plugins/types";

export const pluginsService = {
  listPlugins: async (options?: { revalidate?: number }): Promise<Plugin[]> => {
    return apiClient.get<Plugin[]>(API_ENDPOINTS.plugins, {
      next: { revalidate: options?.revalidate },
    });
  },

  getPlugin: async (
    pluginId: number,
    options?: { revalidate?: number },
  ): Promise<Plugin> => {
    return apiClient.get<Plugin>(API_ENDPOINTS.plugin(pluginId), {
      next: { revalidate: options?.revalidate },
    });
  },

  createPlugin: async (input: PluginCreateInput): Promise<Plugin> => {
    return apiClient.post<Plugin>(API_ENDPOINTS.plugins, input);
  },

  updatePlugin: async (
    pluginId: number,
    input: PluginUpdateInput,
  ): Promise<Plugin> => {
    return apiClient.patch<Plugin>(API_ENDPOINTS.plugin(pluginId), input);
  },

  deletePlugin: async (pluginId: number): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.plugin(pluginId),
    );
  },

  listInstalls: async (options?: {
    revalidate?: number;
  }): Promise<UserPluginInstall[]> => {
    return apiClient.get<UserPluginInstall[]>(API_ENDPOINTS.pluginInstalls, {
      next: { revalidate: options?.revalidate },
    });
  },

  createInstall: async (
    input: PluginInstallCreateInput,
  ): Promise<UserPluginInstall> => {
    return apiClient.post<UserPluginInstall>(
      API_ENDPOINTS.pluginInstalls,
      input,
    );
  },

  updateInstall: async (
    installId: number,
    input: PluginInstallUpdateInput,
  ): Promise<UserPluginInstall> => {
    return apiClient.patch<UserPluginInstall>(
      API_ENDPOINTS.pluginInstall(installId),
      input,
    );
  },

  bulkUpdateInstalls: async (
    input: PluginInstallBulkUpdateInput,
  ): Promise<PluginInstallBulkUpdateResponse> => {
    return apiClient.patch<PluginInstallBulkUpdateResponse>(
      API_ENDPOINTS.pluginInstallsBulk,
      input,
    );
  },

  deleteInstall: async (
    installId: number,
  ): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.pluginInstall(installId),
    );
  },

  importDiscover: async (
    formData: FormData,
  ): Promise<PluginImportDiscoverResponse> => {
    return apiClient.post<PluginImportDiscoverResponse>(
      API_ENDPOINTS.pluginImportDiscover,
      formData,
      { timeoutMs: 5 * 60_000 },
    );
  },

  importCommit: async (
    input: PluginImportCommitInput,
  ): Promise<PluginImportCommitEnqueueResponse> => {
    return apiClient.post<PluginImportCommitEnqueueResponse>(
      API_ENDPOINTS.pluginImportCommit,
      input,
    );
  },

  getImportJob: async (
    jobId: string,
  ): Promise<PluginImportJobStatusResponse> => {
    return apiClient.get<PluginImportJobStatusResponse>(
      API_ENDPOINTS.pluginImportJob(jobId),
      { cache: "no-store" },
    );
  },

  // Backward-compatible alias used by server components
  list: async (options?: { revalidate?: number }) =>
    pluginsService.listPlugins(options),
};
