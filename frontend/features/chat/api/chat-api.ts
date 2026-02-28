/**
 * Chat Service – Session execution and messaging.
 *
 * This module is the **API orchestration layer** for the chat feature.
 * Complex business logic (message parsing, file-tree building) has been
 * extracted into dedicated modules:
 *
 * - `../services/message-parser.ts` – raw API messages → UI-friendly ChatMessage[]
 * - `../services/file-tree-builder.ts` – flat file list → hierarchical tree
 */

import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  ExecutionSession,
  FileNode,
  SessionCancelRequest,
  SessionCancelResponse,
  SessionBranchRequest,
  SessionBranchResponse,
  SessionEditMessageRequest,
  MessageAttachmentsResponse,
  MessageResponse,
  SessionRegenerateRequest,
  SessionResponse,
  SessionUpdateRequest,
  ToolExecutionResponse,
  ComputerBrowserScreenshotResponse,
  TaskEnqueueRequest,
  TaskEnqueueResponse,
  TaskConfig,
  InputFile,
  RunResponse,
} from "@/features/chat/types";

import {
  parseMessages,
  parseConfigSnapshot,
  type RawApiMessage,
} from "../services/message-parser";
import { buildFileTree } from "../services/file-tree-builder";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildQuery(params?: Record<string, string | number | undefined>) {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) searchParams.append(key, String(value));
  }
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

function toExecutionSession(
  session: SessionResponse,
  progress = 0,
): ExecutionSession {
  return {
    session_id: session.session_id,
    time: session.updated_at,
    status: session.status as ExecutionSession["status"],
    progress,
    state_patch: session.state_patch ?? {},
    config_snapshot: parseConfigSnapshot(session.config_snapshot),
    task_name: undefined,
    user_prompt: undefined,
    title: session.title,
  };
}

function createDefaultSession(sessionId: string): ExecutionSession {
  return {
    session_id: sessionId,
    time: new Date().toISOString(),
    status: "pending",
    progress: 0,
    state_patch: {},
    task_name: undefined,
    user_prompt: undefined,
    title: null,
  };
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const chatService = {
  // ---- Session CRUD ----

  listSessions: async (params?: {
    user_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = buildQuery(params);
    return apiClient.get<SessionResponse[]>(
      `${API_ENDPOINTS.sessions}${query}`,
    );
  },

  getSessionRaw: async (sessionId: string) => {
    return apiClient.get<SessionResponse>(API_ENDPOINTS.session(sessionId));
  },

  getExecutionSession: async (
    sessionId: string,
    currentProgress = 0,
  ): Promise<ExecutionSession> => {
    try {
      const session = await chatService.getSessionRaw(sessionId);
      return toExecutionSession(session, currentProgress);
    } catch (error) {
      console.error("[Chat Service] Failed to get session:", error);
      return createDefaultSession(sessionId);
    }
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    return apiClient.delete(API_ENDPOINTS.session(sessionId));
  },

  updateSession: async (
    sessionId: string,
    payload: SessionUpdateRequest,
  ): Promise<SessionResponse> => {
    return apiClient.patch<SessionResponse>(
      API_ENDPOINTS.session(sessionId),
      payload,
    );
  },

  cancelSession: async (
    sessionId: string,
    payload?: SessionCancelRequest,
  ): Promise<SessionCancelResponse> => {
    return apiClient.post<SessionCancelResponse>(
      API_ENDPOINTS.sessionCancel(sessionId),
      payload ?? {},
    );
  },

  branchSession: async (
    sessionId: string,
    payload: SessionBranchRequest,
  ): Promise<SessionBranchResponse> => {
    return apiClient.post<SessionBranchResponse>(
      API_ENDPOINTS.sessionBranch(sessionId),
      payload,
    );
  },

  regenerateMessage: async (
    sessionId: string,
    payload: SessionRegenerateRequest,
  ): Promise<TaskEnqueueResponse> => {
    return apiClient.post<TaskEnqueueResponse>(
      API_ENDPOINTS.sessionRegenerate(sessionId),
      payload,
    );
  },

  editMessageAndRegenerate: async (
    sessionId: string,
    payload: SessionEditMessageRequest,
  ): Promise<TaskEnqueueResponse> => {
    return apiClient.post<TaskEnqueueResponse>(
      API_ENDPOINTS.sessionEditMessage(sessionId),
      payload,
    );
  },

  // ---- Task enqueue ----

  enqueueTask: async (
    request: TaskEnqueueRequest,
  ): Promise<TaskEnqueueResponse> => {
    return apiClient.post<TaskEnqueueResponse>(API_ENDPOINTS.tasks, request);
  },

  createSession: async (
    prompt: string,
    config?: TaskConfig | null,
    projectId?: string | null,
    schedule?: {
      schedule_mode?: string;
      timezone?: string;
      scheduled_at?: string;
    },
    permission_mode?: string,
  ): Promise<TaskEnqueueResponse> => {
    return chatService.enqueueTask({
      prompt,
      config,
      permission_mode,
      schedule_mode: schedule?.schedule_mode || "immediate",
      timezone: schedule?.timezone,
      scheduled_at: schedule?.scheduled_at,
      project_id: projectId,
    });
  },

  sendMessage: async (
    sessionId: string,
    content: string,
    attachments?: InputFile[],
  ): Promise<TaskEnqueueResponse> => {
    return chatService.enqueueTask({
      prompt: content,
      session_id: sessionId,
      schedule_mode: "immediate",
      config: attachments?.length ? { input_files: attachments } : undefined,
    });
  },

  // ---- Runs & tool executions ----

  getRunsBySession: async (
    sessionId: string,
    params?: { limit?: number; offset?: number },
  ): Promise<RunResponse[]> => {
    const query = buildQuery(params);
    return apiClient.get<RunResponse[]>(
      `${API_ENDPOINTS.runsBySession(sessionId)}${query}`,
    );
  },

  getToolExecutions: async (
    sessionId: string,
    params?: { limit?: number; offset?: number },
  ): Promise<ToolExecutionResponse[]> => {
    const query = buildQuery(params);
    return apiClient.get<ToolExecutionResponse[]>(
      `${API_ENDPOINTS.sessionToolExecutions(sessionId)}${query}`,
    );
  },

  getBrowserScreenshot: async (
    sessionId: string,
    toolUseId: string,
  ): Promise<ComputerBrowserScreenshotResponse> => {
    return apiClient.get<ComputerBrowserScreenshotResponse>(
      API_ENDPOINTS.sessionBrowserScreenshot(sessionId, toolUseId),
    );
  },

  // ---- Messages ----

  getMessages: async (
    sessionId: string,
    options?: { realUserMessageIds?: number[] },
  ) => {
    try {
      const rawMessages = await apiClient.get<RawApiMessage[]>(
        API_ENDPOINTS.sessionMessagesWithFiles(sessionId),
      );
      const parsed = parseMessages(rawMessages, options?.realUserMessageIds);
      return parsed;
    } catch (error) {
      console.error("[Chat Service] Failed to get messages:", error);
      return { messages: [] };
    }
  },

  getMessagesBase: async (
    sessionId: string,
    options?: { realUserMessageIds?: number[] },
  ) => {
    try {
      const baseMessages = await apiClient.get<MessageResponse[]>(
        API_ENDPOINTS.sessionMessages(sessionId),
      );
      const rawMessages: RawApiMessage[] = baseMessages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        created_at: message.created_at,
        updated_at: message.updated_at,
      }));
      return parseMessages(rawMessages, options?.realUserMessageIds);
    } catch (error) {
      console.error("[Chat Service] Failed to get base messages:", error);
      return { messages: [] };
    }
  },

  getMessageAttachments: async (
    sessionId: string,
  ): Promise<Record<number, InputFile[]>> => {
    try {
      const response = await apiClient.get<MessageAttachmentsResponse[]>(
        API_ENDPOINTS.sessionMessageAttachments(sessionId),
      );
      return response.reduce<Record<number, InputFile[]>>((acc, item) => {
        acc[item.message_id] = item.attachments ?? [];
        return acc;
      }, {});
    } catch (error) {
      console.error("[Chat Service] Failed to get message attachments:", error);
      return {};
    }
  },

  // ---- Files ----

  getFiles: async (sessionId?: string): Promise<FileNode[]> => {
    if (!sessionId) return [];

    try {
      let rawFiles: FileNode[] = [];

      try {
        rawFiles = await apiClient.get<FileNode[]>(
          API_ENDPOINTS.sessionWorkspaceFiles(sessionId),
        );
      } catch (err) {
        console.warn("[Chat Service] Failed to get workspace files:", err);
      }

      // Fallback to file changes from session state
      if (!rawFiles || rawFiles.length === 0) {
        try {
          const session = await chatService.getSessionRaw(sessionId);
          const fileChanges =
            session.state_patch?.workspace_state?.file_changes || [];
          rawFiles = fileChanges.map((change) => ({
            id: change.path,
            name: change.path.split("/").pop() || change.path,
            path: change.path,
            type: "file",
          }));
        } catch (err) {
          console.error(
            "[Chat Service] Fallback to session state failed:",
            err,
          );
        }
      }

      return buildFileTree(rawFiles);
    } catch (error) {
      console.error("[Chat Service] Failed to get files:", error);
      return [];
    }
  },
};
