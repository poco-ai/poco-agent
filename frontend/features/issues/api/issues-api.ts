import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  AgentAssignment,
  AgentAssignmentActionResult,
  WorkspaceBoard,
  WorkspaceBoardInput,
  WorkspaceIssue,
  WorkspaceIssueMoveInput,
} from "@/features/issues/model/types";

export const issuesApi = {
  listBoards: async (workspaceId: string): Promise<WorkspaceBoard[]> => {
    return apiClient.get<WorkspaceBoard[]>(API_ENDPOINTS.workspaceBoards(workspaceId));
  },

  createBoard: async (
    workspaceId: string,
    input: WorkspaceBoardInput,
  ): Promise<WorkspaceBoard> => {
    return apiClient.post<WorkspaceBoard>(
      API_ENDPOINTS.workspaceBoards(workspaceId),
      input,
    );
  },

  updateBoard: async (
    workspaceId: string,
    boardId: string,
    input: WorkspaceBoardInput,
  ): Promise<WorkspaceBoard> => {
    return apiClient.patch<WorkspaceBoard>(
      API_ENDPOINTS.workspaceBoard(workspaceId, boardId),
      input,
    );
  },

  deleteBoard: async (
    workspaceId: string,
    boardId: string,
  ): Promise<WorkspaceBoard> => {
    return apiClient.delete<WorkspaceBoard>(
      API_ENDPOINTS.workspaceBoard(workspaceId, boardId),
    );
  },

  listIssues: async (boardId: string): Promise<WorkspaceIssue[]> => {
    return apiClient.get<WorkspaceIssue[]>(API_ENDPOINTS.workspaceIssues(boardId));
  },

  createIssue: async (
    boardId: string,
    input: {
      title: string;
      description?: string | null;
      assignee_preset_id?: number | null;
      assignee_user_id?: string | null;
      trigger_mode?: "persistent_sandbox" | "scheduled_task";
      schedule_cron?: string | null;
      assignment_prompt?: string | null;
    },
  ): Promise<WorkspaceIssue> => {
    return apiClient.post<WorkspaceIssue>(
      API_ENDPOINTS.workspaceIssues(boardId),
      input,
    );
  },

  getIssue: async (issueId: string): Promise<WorkspaceIssue> => {
    return apiClient.get<WorkspaceIssue>(API_ENDPOINTS.workspaceIssueDetail(issueId));
  },

  updateIssue: async (
    boardId: string,
    issueId: string,
    input: {
      title?: string;
      description?: string | null;
      status?: string | null;
      priority?: string | null;
      assignee_preset_id?: number | null;
      assignee_user_id?: string | null;
      related_project_id?: string | null;
      trigger_mode?: "persistent_sandbox" | "scheduled_task";
      schedule_cron?: string | null;
      assignment_prompt?: string | null;
    },
  ): Promise<WorkspaceIssue> => {
    return apiClient.patch<WorkspaceIssue>(
      API_ENDPOINTS.workspaceIssue(boardId, issueId),
      input,
    );
  },

  moveIssue: async (
    issueId: string,
    input: WorkspaceIssueMoveInput,
  ): Promise<WorkspaceIssue> => {
    return apiClient.post<WorkspaceIssue>(
      API_ENDPOINTS.workspaceIssueMove(issueId),
      input,
    );
  },

  deleteIssue: async (
    boardId: string,
    issueId: string,
  ): Promise<WorkspaceIssue> => {
    return apiClient.delete<WorkspaceIssue>(
      API_ENDPOINTS.workspaceIssue(boardId, issueId),
    );
  },

  getAssignment: async (issueId: string): Promise<AgentAssignment | null> => {
    return apiClient.get<AgentAssignment | null>(
      API_ENDPOINTS.workspaceIssueAgentAssignment(issueId),
    );
  },

  triggerAssignment: async (
    issueId: string,
  ): Promise<AgentAssignmentActionResult> => {
    return apiClient.post<AgentAssignmentActionResult>(
      API_ENDPOINTS.workspaceIssueAgentTrigger(issueId),
      {},
    );
  },

  retryAssignment: async (
    issueId: string,
  ): Promise<AgentAssignmentActionResult> => {
    return apiClient.post<AgentAssignmentActionResult>(
      API_ENDPOINTS.workspaceIssueAgentRetry(issueId),
      {},
    );
  },

  cancelAssignment: async (
    issueId: string,
  ): Promise<AgentAssignmentActionResult> => {
    return apiClient.post<AgentAssignmentActionResult>(
      API_ENDPOINTS.workspaceIssueAgentCancel(issueId),
      {},
    );
  },

  releaseAssignment: async (
    issueId: string,
  ): Promise<AgentAssignmentActionResult> => {
    return apiClient.post<AgentAssignmentActionResult>(
      API_ENDPOINTS.workspaceIssueAgentRelease(issueId),
      {},
    );
  },
};
