import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { ModelConfigResponse } from "@/features/chat/types";

export const modelConfigService = {
  get: async (): Promise<ModelConfigResponse> => {
    return apiClient.get<ModelConfigResponse>(API_ENDPOINTS.models);
  },
};
