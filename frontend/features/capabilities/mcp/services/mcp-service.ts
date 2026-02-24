import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  McpServer,
  McpServerCreateInput,
  McpServerUpdateInput,
  McpInstallBulkUpdateInput,
  McpInstallBulkUpdateResponse,
  UserMcpInstall,
  UserMcpInstallCreateInput,
  UserMcpInstallUpdateInput,
} from "@/features/capabilities/mcp/types";

export const mcpService = {
  listServers: async (options?: {
    revalidate?: number;
  }): Promise<McpServer[]> => {
    return apiClient.get<McpServer[]>(API_ENDPOINTS.mcpServers, {
      next: { revalidate: options?.revalidate },
    });
  },

  getServer: async (
    serverId: number,
    options?: { revalidate?: number },
  ): Promise<McpServer> => {
    return apiClient.get<McpServer>(API_ENDPOINTS.mcpServer(serverId), {
      next: { revalidate: options?.revalidate },
    });
  },

  createServer: async (input: McpServerCreateInput): Promise<McpServer> => {
    return apiClient.post<McpServer>(API_ENDPOINTS.mcpServers, input);
  },

  updateServer: async (
    serverId: number,
    input: McpServerUpdateInput,
  ): Promise<McpServer> => {
    return apiClient.patch<McpServer>(API_ENDPOINTS.mcpServer(serverId), input);
  },

  deleteServer: async (serverId: number): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.mcpServer(serverId),
    );
  },

  listInstalls: async (options?: {
    revalidate?: number;
  }): Promise<UserMcpInstall[]> => {
    return apiClient.get<UserMcpInstall[]>(API_ENDPOINTS.mcpInstalls, {
      next: { revalidate: options?.revalidate },
    });
  },

  createInstall: async (
    input: UserMcpInstallCreateInput,
  ): Promise<UserMcpInstall> => {
    return apiClient.post<UserMcpInstall>(API_ENDPOINTS.mcpInstalls, input);
  },

  updateInstall: async (
    installId: number,
    input: UserMcpInstallUpdateInput,
  ): Promise<UserMcpInstall> => {
    return apiClient.patch<UserMcpInstall>(
      API_ENDPOINTS.mcpInstall(installId),
      input,
    );
  },

  bulkUpdateInstalls: async (
    input: McpInstallBulkUpdateInput,
  ): Promise<McpInstallBulkUpdateResponse> => {
    return apiClient.patch<McpInstallBulkUpdateResponse>(
      API_ENDPOINTS.mcpInstallsBulk,
      input,
    );
  },

  deleteInstall: async (
    installId: number,
  ): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.mcpInstall(installId),
    );
  },
};
