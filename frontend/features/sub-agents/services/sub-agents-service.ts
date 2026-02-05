import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentUpdateInput,
} from "@/features/sub-agents/types";

export const subAgentsService = {
  list: async (options?: { revalidate?: number }): Promise<SubAgent[]> => {
    return apiClient.get<SubAgent[]>(API_ENDPOINTS.subAgents, {
      next: { revalidate: options?.revalidate },
    });
  },

  get: async (
    subAgentId: number,
    options?: { revalidate?: number },
  ): Promise<SubAgent> => {
    return apiClient.get<SubAgent>(API_ENDPOINTS.subAgent(subAgentId), {
      next: { revalidate: options?.revalidate },
    });
  },

  create: async (input: SubAgentCreateInput): Promise<SubAgent> => {
    return apiClient.post<SubAgent>(API_ENDPOINTS.subAgents, input);
  },

  update: async (
    subAgentId: number,
    input: SubAgentUpdateInput,
  ): Promise<SubAgent> => {
    return apiClient.patch<SubAgent>(API_ENDPOINTS.subAgent(subAgentId), input);
  },

  remove: async (subAgentId: number): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.subAgent(subAgentId),
    );
  },
};
