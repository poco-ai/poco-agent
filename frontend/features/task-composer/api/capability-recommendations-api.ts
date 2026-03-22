import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { CapabilityRecommendationsResponse } from "@/features/task-composer/types/capability-recommendation";

export const capabilityRecommendationsService = {
  list: async (
    input: {
      query: string;
      limit?: number;
    },
    options?: { signal?: AbortSignal },
  ): Promise<CapabilityRecommendationsResponse> => {
    return apiClient.post<CapabilityRecommendationsResponse>(
      API_ENDPOINTS.capabilityRecommendations,
      {
        query: input.query,
        limit: input.limit ?? 3,
      },
      { signal: options?.signal },
    );
  },
};
