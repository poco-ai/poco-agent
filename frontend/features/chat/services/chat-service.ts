/**
 * Chat Service - Session execution and messaging
 */

import "server-only";

import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import type {
  ExecutionSession,
  FileNode,
  ChatMessage,
  MessageBlock,
  SessionResponse,
  TaskEnqueueRequest,
  TaskEnqueueResponse,
  TaskConfig,
} from "@/features/chat/types";

interface MessageContentBlock {
  _type: string;
  // ToolUseBlock fields
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  // ToolResultBlock fields
  tool_use_id?: string;
  content?: string;
  is_error?: boolean;
  // TextBlock fields
  text?: string;
}

interface MessageContentShape {
  _type?: string;
  subtype?: string;
  content?: MessageContentBlock[];
  text?: string;
}

function toExecutionSession(
  session: SessionResponse,
  progress: number = 0,
): ExecutionSession {
  return {
    session_id: session.session_id,
    time: session.updated_at,
    status:
      session.status === "completed"
        ? "completed"
        : session.status === "failed"
          ? "failed"
          : session.status === "running"
            ? "running"
            : "accepted",
    progress,
    state_patch: session.state_patch ?? {},
    task_name: undefined,
    user_prompt: undefined,
  };
}

function createDefaultSession(sessionId: string): ExecutionSession {
  return {
    session_id: sessionId,
    time: new Date().toISOString(),
    status: "accepted",
    progress: 0,
    state_patch: {},
    task_name: undefined,
    user_prompt: undefined,
  };
}

function buildQuery(params?: Record<string, string | number | undefined>) {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) searchParams.append(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export const chatService = {
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
    currentProgress: number = 0,
  ): Promise<ExecutionSession> => {
    try {
      const session = await chatService.getSessionRaw(sessionId);
      return toExecutionSession(session, currentProgress);
    } catch (error) {
      console.error("[Chat Service] Failed to get session:", error);
      return createDefaultSession(sessionId);
    }
  },

  enqueueTask: async (request: TaskEnqueueRequest): Promise<TaskEnqueueResponse> => {
    console.log("[enqueueTask] request:", JSON.stringify(request));
    try {
      const result = await apiClient.post<TaskEnqueueResponse>(
        API_ENDPOINTS.tasks,
        request,
      );
      console.log("[enqueueTask] result:", JSON.stringify(result));
      return result;
    } catch (error) {
      console.error("[enqueueTask] error:", error);
      throw error;
    }
  },

  createSession: async (
    prompt: string,
    config?: TaskConfig | null,
  ): Promise<TaskEnqueueResponse> => {
    return chatService.enqueueTask({
      prompt,
      config,
      schedule_mode: "immediate",
    });
  },

  sendMessage: async (
    sessionId: string,
    content: string,
  ): Promise<TaskEnqueueResponse> => {
    return chatService.enqueueTask({
      prompt: content,
      session_id: sessionId,
      schedule_mode: "immediate",
    });
  },

  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    try {
      const messages = await apiClient.get<
        {
          id: number;
          role: string;
          content: Record<string, unknown>;
          text_preview: string | null;
          created_at: string;
          updated_at: string;
        }[]
      >(API_ENDPOINTS.sessionMessages(sessionId));

      const processedMessages: ChatMessage[] = [];
      let currentAssistantMessage: ChatMessage | null = null;

      for (const msg of messages) {
        const contentObj = msg.content as MessageContentShape;
        if (
          contentObj._type === "SystemMessage" &&
          contentObj.subtype === "init"
        ) {
          continue;
        }

        if (msg.role === "assistant" && contentObj.content) {
          const blocks = contentObj.content;
          const toolUseBlocks = blocks.filter(
            (b) => b._type === "ToolUseBlock",
          );

          if (toolUseBlocks.length > 0) {
            if (!currentAssistantMessage) {
              currentAssistantMessage = {
                id: msg.id.toString(),
                role: "assistant",
                content: [],
                status: "completed",
                timestamp: msg.created_at,
              };
              processedMessages.push(currentAssistantMessage);
            }

            const existingBlocks =
              currentAssistantMessage.content as MessageBlock[];

            const uiToolBlocks = toolUseBlocks.map((b) => ({
              _type: "ToolUseBlock" as const,
              id: b.id || "",
              name: b.name || "",
              input: b.input || {},
            }));

            currentAssistantMessage.content = [
              ...existingBlocks,
              ...uiToolBlocks,
            ];
            continue;
          }
        }

        if (msg.role === "user" && contentObj.content) {
          const blocks = contentObj.content;
          const toolResultBlocks = blocks.filter(
            (b) => b._type === "ToolResultBlock",
          );

          if (toolResultBlocks.length > 0 && currentAssistantMessage) {
            const uiResultBlocks = toolResultBlocks.map((b) => ({
              _type: "ToolResultBlock" as const,
              tool_use_id: b.tool_use_id || "",
              content:
                typeof b.content === "string"
                  ? b.content
                  : JSON.stringify(b.content),
              is_error: !!b.is_error,
            }));
            const existingBlocks =
              currentAssistantMessage.content as MessageBlock[];
            currentAssistantMessage.content = [
              ...existingBlocks,
              ...uiResultBlocks,
            ];
            continue;
          }
        }

        let textContent = "";
        if (contentObj.text) {
          textContent = String(contentObj.text);
        } else if (contentObj.content && Array.isArray(contentObj.content)) {
          const textBlock = contentObj.content.find(
            (b) => b._type === "TextBlock",
          );
          if (textBlock) textContent = textBlock.text || "";
        }

        if (!textContent && msg.text_preview) {
          textContent = msg.text_preview;
        }

        if (textContent) {
          if (msg.role === "user") {
            currentAssistantMessage = null;
            processedMessages.push({
              id: msg.id.toString(),
              role: "user",
              content: textContent,
              status: "completed",
              timestamp: msg.created_at,
            });
          } else {
            if (currentAssistantMessage) {
              const existingBlocks =
                currentAssistantMessage.content as MessageBlock[];
              existingBlocks.push({
                _type: "TextBlock",
                text: textContent,
              });
            } else {
              processedMessages.push({
                id: msg.id.toString(),
                role: "assistant",
                content: textContent,
                status: "completed",
                timestamp: msg.created_at,
              });
            }
          }
        }
      }

      return processedMessages;
    } catch (error) {
      console.error("[Chat Service] Failed to get messages:", error);
      return [];
    }
  },

  getFiles: async (sessionId?: string): Promise<FileNode[]> => {
    if (!sessionId) return [];

    try {
      let rawFiles: FileNode[];
      try {
        rawFiles = await apiClient.get<FileNode[]>(
          API_ENDPOINTS.sessionWorkspaceFiles(sessionId),
        );
      } catch {
        const session = await chatService.getSessionRaw(sessionId);
        const fileChanges =
          session.state_patch?.workspace_state?.file_changes || [];
        rawFiles = fileChanges.map((change) => ({
          id: change.path,
          name: change.path.split("/").pop() || change.path,
          path: change.path,
          type: "file",
        }));
      }

      const buildFileTree = (nodes: FileNode[]): FileNode[] => {
        const nodeMap = new Map<string, FileNode>();
        const rootNodes: FileNode[] = [];

        const flatten = (list: FileNode[]): FileNode[] => {
          let result: FileNode[] = [];
          for (const item of list) {
            result.push(item);
            if (item.children) {
              result = result.concat(flatten(item.children));
            }
          }
          return result;
        };

        const allNodes = flatten(nodes);

        allNodes.forEach((node) => {
          nodeMap.set(node.path, { ...node, children: [] });
        });

        const processedPaths = new Set<string>();
        const sortedPaths = Array.from(nodeMap.keys()).sort();

        sortedPaths.forEach((path) => {
          if (processedPaths.has(path)) return;

          const parts = path.split("/");
          let currentPath = "";

          parts.forEach((part, index) => {
            const parentPath = currentPath;
            currentPath = currentPath ? `${currentPath}/${part}` : part;

            if (processedPaths.has(currentPath)) return;

            let node = nodeMap.get(currentPath);

            if (!node) {
              const isLastPart = index === parts.length - 1;
              const originalNode = nodeMap.get(path);

              node = {
                id: currentPath,
                name: part,
                path: currentPath,
                type: isLastPart && originalNode ? originalNode.type : "folder",
                children: [],
              };
              nodeMap.set(currentPath, node);
            }

            if (parentPath) {
              const parent = nodeMap.get(parentPath);
              if (parent) {
                if (!parent.children) parent.children = [];
                if (!parent.children.find((c) => c.path === node!.path)) {
                  parent.children.push(node);
                }
              }
            } else {
              if (!rootNodes.find((n) => n.path === node!.path)) {
                rootNodes.push(node);
              }
            }

            processedPaths.add(currentPath);
          });
        });

        const sortTree = (list: FileNode[]) => {
          list.sort((a, b) => {
            if (a.type !== b.type) {
              return a.type === "folder" ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
          });
          list.forEach((node) => {
            if (node.children) sortTree(node.children);
          });
        };

        sortTree(rootNodes);
        return rootNodes;
      };

      const removeEmptyFolders = (nodes: FileNode[]): FileNode[] => {
        return nodes
          .map((node) => {
            if (node.type === "folder" && node.children) {
              node.children = removeEmptyFolders(node.children);
              if (node.children.length === 0) {
                return null;
              }
            }
            return node;
          })
          .filter((node): node is FileNode => node !== null);
      };

      let tree = buildFileTree(rawFiles);
      tree = removeEmptyFolders(tree);

      return tree;
    } catch (error) {
      console.error("[Chat Service] Failed to get files:", error);
      return [];
    }
  },
};
