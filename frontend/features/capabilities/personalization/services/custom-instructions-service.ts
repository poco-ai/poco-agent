import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  CustomInstructionsSettings,
  CustomInstructionsUpsertInput,
} from "@/features/capabilities/personalization/types";

export const customInstructionsService = {
  get: async (): Promise<CustomInstructionsSettings> => {
    return apiClient.get<CustomInstructionsSettings>(
      API_ENDPOINTS.customInstructions,
    );
  },

  upsert: async (
    input: CustomInstructionsUpsertInput,
  ): Promise<CustomInstructionsSettings> => {
    return apiClient.put<CustomInstructionsSettings>(
      API_ENDPOINTS.customInstructions,
      input,
    );
  },

  remove: async (): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.customInstructions,
    );
  },
};
