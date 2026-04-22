import { API_ENDPOINTS, apiClient } from "../../../services/api-client.ts";
import type { LocalFilesystemSupport } from "@/features/task-composer/types/local-filesystem";

export const localFilesystemApi = {
  getSupport: async (): Promise<LocalFilesystemSupport> => {
    return apiClient.get<LocalFilesystemSupport>(
      API_ENDPOINTS.filesystemSupport,
    );
  },
};
