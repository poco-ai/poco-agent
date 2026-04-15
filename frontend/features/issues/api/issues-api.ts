import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  WorkspaceBoard,
  WorkspaceIssue,
} from "@/features/issues/model/types";

export const issuesApi = {
  listBoards: async (workspaceId: string): Promise<WorkspaceBoard[]> => {
    return apiClient.get<WorkspaceBoard[]>(API_ENDPOINTS.workspaceBoards(workspaceId));
  },

  createBoard: async (
    workspaceId: string,
    input: { name: string; description?: string | null },
  ): Promise<WorkspaceBoard> => {
    return apiClient.post<WorkspaceBoard>(
      API_ENDPOINTS.workspaceBoards(workspaceId),
      input,
    );
  },

  listIssues: async (boardId: string): Promise<WorkspaceIssue[]> => {
    return apiClient.get<WorkspaceIssue[]>(API_ENDPOINTS.workspaceIssues(boardId));
  },

  createIssue: async (
    boardId: string,
    input: { title: string; description?: string | null },
  ): Promise<WorkspaceIssue> => {
    return apiClient.post<WorkspaceIssue>(
      API_ENDPOINTS.workspaceIssues(boardId),
      input,
    );
  },
};
