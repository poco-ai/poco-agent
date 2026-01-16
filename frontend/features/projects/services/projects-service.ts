import "server-only";

import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";

export const projectsService = {
  listProjects: async (_options?: {
    revalidate?: number;
  }): Promise<ProjectItem[]> => {
    // TODO: Projects API temporarily disabled
    return [];
    // try {
    //   return await apiClient.get<ProjectItem[]>(API_ENDPOINTS.projects, {
    //     next: { revalidate: options?.revalidate },
    //   });
    // } catch (error) {
    //   console.warn(
    //     "[Projects] Failed to fetch projects, using empty list",
    //     error,
    //   );
    //   return [];
    // }
  },

  createProject: async (name: string): Promise<ProjectItem> => {
    // TODO: Projects API temporarily disabled - using local fallback only
    return {
      id: `project-${Date.now()}`,
      name,
      taskCount: 0,
    };
    // try {
    //   return await apiClient.post<ProjectItem>(API_ENDPOINTS.projects, {
    //     name,
    //   });
    // } catch (error) {
    //   console.warn(
    //     "[Projects] Create project API unavailable, using local fallback",
    //     error,
    //   );
    //   return {
    //     id: `project-${Date.now()}`,
    //     name,
    //     taskCount: 0,
    //   };
    // }
  },
};

export const tasksService = {
  listHistory: async (options?: {
    revalidate?: number;
  }): Promise<TaskHistoryItem[]> => {
    try {
      return await apiClient.get<TaskHistoryItem[]>(
        API_ENDPOINTS.sessions,
        {
          next: { revalidate: options?.revalidate },
        },
      );
    } catch (error) {
      console.warn(
        "[Tasks] Failed to fetch task history, using empty list",
        error,
      );
      return [];
    }
  },
};
