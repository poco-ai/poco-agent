import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { ExecutionSettings } from "@/features/settings/types";

export async function getExecutionSettings(): Promise<ExecutionSettings> {
  return apiClient.get<ExecutionSettings>(API_ENDPOINTS.executionSettings, {
    cache: "no-store",
  });
}

export async function updateExecutionSettings(
  settings: ExecutionSettings,
): Promise<ExecutionSettings> {
  return apiClient.patch<ExecutionSettings>(API_ENDPOINTS.executionSettings, {
    settings,
  });
}
