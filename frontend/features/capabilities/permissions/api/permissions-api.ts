import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { ExecutionSettings } from "@/features/settings/types";
import type { PermissionPolicy } from "../types";

export async function getPermissionPolicy(): Promise<PermissionPolicy> {
  const settings = await apiClient.get<ExecutionSettings>(
    API_ENDPOINTS.executionSettings,
    { cache: "no-store" },
  );
  const p = settings.permissions as unknown;
  if (p && typeof p === "object" && "version" in p) {
    return p as PermissionPolicy;
  }
  return {
    version: "v1",
    mode: "audit",
    default_action: "allow",
    preset_source: null,
    rules: [],
  };
}

export async function updatePermissionPolicy(
  policy: PermissionPolicy,
): Promise<PermissionPolicy> {
  const settings = await apiClient.get<ExecutionSettings>(
    API_ENDPOINTS.executionSettings,
    { cache: "no-store" },
  );
  const updated = await apiClient.patch<ExecutionSettings>(
    API_ENDPOINTS.executionSettings,
    { settings: { ...settings, permissions: policy } },
  );
  return (updated.permissions as unknown as PermissionPolicy) ?? policy;
}
