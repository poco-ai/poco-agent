import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  EnvVar,
  EnvVarCreateInput,
  EnvVarUpdateInput,
} from "@/features/capabilities/env-vars/types";

export const envVarsService = {
  list: async (options?: { revalidate?: number }): Promise<EnvVar[]> => {
    return apiClient.get<EnvVar[]>(API_ENDPOINTS.envVars, {
      next: { revalidate: options?.revalidate },
    });
  },

  create: async (input: EnvVarCreateInput): Promise<EnvVar> => {
    return apiClient.post<EnvVar>(API_ENDPOINTS.envVars, input);
  },

  update: async (
    envVarId: number,
    input: EnvVarUpdateInput,
  ): Promise<EnvVar> => {
    return apiClient.patch<EnvVar>(API_ENDPOINTS.envVar(envVarId), input);
  },

  remove: async (envVarId: number): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.envVar(envVarId),
    );
  },
};
