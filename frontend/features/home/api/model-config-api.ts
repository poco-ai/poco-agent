import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  ModelConfigResponse,
  ModelProvider,
  ProviderModelSettingsUpdateInput,
} from "@/features/chat/types";

export const modelConfigService = {
  get: async (): Promise<ModelConfigResponse> => {
    return apiClient.get<ModelConfigResponse>(API_ENDPOINTS.models);
  },

  updateProviderModels: async (
    providerId: string,
    input: ProviderModelSettingsUpdateInput,
  ): Promise<ModelProvider> => {
    return apiClient.put<ModelProvider>(
      API_ENDPOINTS.modelProvider(providerId),
      input,
    );
  },
};
