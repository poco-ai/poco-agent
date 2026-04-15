import { ApiError } from "@/lib/errors";
import type { ApiResponse } from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const API_PREFIX = "/api/v1";

/**
 * Centralized API endpoint definitions.
 *
 * Static endpoints are plain strings; dynamic endpoints are factory functions
 * that accept the required identifier and return the path segment.
 */
export const API_ENDPOINTS = {
  // Sessions
  sessions: "/sessions",
  sessionsWithTitles: "/sessions/list-with-titles",
  session: (sessionId: string) => `/sessions/${sessionId}`,
  sessionCancel: (sessionId: string) => `/sessions/${sessionId}/cancel`,
  sessionBranch: (sessionId: string) => `/sessions/${sessionId}/branch`,
  sessionRegenerate: (sessionId: string) => `/sessions/${sessionId}/regenerate`,
  sessionEditMessage: (sessionId: string) =>
    `/sessions/${sessionId}/edit-message`,
  sessionQueuedQueries: (sessionId: string) =>
    `/sessions/${sessionId}/queued-queries`,
  sessionQueuedQuery: (sessionId: string, itemId: string) =>
    `/sessions/${sessionId}/queued-queries/${itemId}`,
  sessionQueuedQuerySendNow: (sessionId: string, itemId: string) =>
    `/sessions/${sessionId}/queued-queries/${itemId}/send-now`,
  sessionState: (sessionId: string) => `/sessions/${sessionId}/state`,
  sessionMessages: (sessionId: string) => `/sessions/${sessionId}/messages`,
  sessionMessagesDelta: (sessionId: string) =>
    `/sessions/${sessionId}/messages/delta`,
  sessionMessageAttachments: (sessionId: string) =>
    `/sessions/${sessionId}/message-attachments`,
  sessionMessageAttachmentsDelta: (sessionId: string) =>
    `/sessions/${sessionId}/message-attachments/delta`,
  sessionMessagesWithFiles: (sessionId: string) =>
    `/sessions/${sessionId}/messages-with-files`,
  sessionMessagesWithFilesDelta: (sessionId: string) =>
    `/sessions/${sessionId}/messages-with-files/delta`,
  sessionToolExecutions: (sessionId: string) =>
    `/sessions/${sessionId}/tool-executions`,
  sessionToolExecutionsDelta: (sessionId: string) =>
    `/sessions/${sessionId}/tool-executions/delta`,
  sessionBrowserScreenshot: (sessionId: string, toolUseId: string) =>
    `/sessions/${sessionId}/computer/browser/${toolUseId}`,
  sessionUsage: (sessionId: string) => `/sessions/${sessionId}/usage`,
  usageAnalytics: "/usage/analytics",
  sessionWorkspaceFiles: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/files`,
  sessionLocalMountFiles: (sessionId: string) =>
    `/sessions/${sessionId}/local-mounts/files`,
  sessionLocalMountFile: (sessionId: string) =>
    `/sessions/${sessionId}/local-mounts/file`,
  sessionLocalMountFolderArchive: (sessionId: string) =>
    `/sessions/${sessionId}/local-mounts/folder-archive`,
  filesystemSupport: "/filesystem/support",
  sessionWorkspaceArchive: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/archive`,
  sessionWorkspaceFolderArchive: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/folder-archive`,
  sessionWorkspaceSubmitSkill: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/submit-skill`,

  // User Input Requests
  userInputRequests: "/user-input-requests",
  userInputRequest: (requestId: string) => `/user-input-requests/${requestId}`,
  userInputAnswer: (requestId: string) =>
    `/user-input-requests/${requestId}/answer`,

  // Tasks
  tasks: "/tasks",

  // Memories
  memories: "/memories",
  memoriesSearch: "/memories/search",
  memory: (memoryId: string) => `/memories/${memoryId}`,
  memoryHistory: (memoryId: string) => `/memories/${memoryId}/history`,
  memoryCreateJob: (jobId: string) => `/memories/jobs/${jobId}`,
  memoryActiveCreateJob: "/memories/jobs/active",

  // Search
  search: "/search",
  capabilityRecommendations: "/capability-recommendations",

  // Models
  models: "/models",

  // Runs
  runsBySession: (sessionId: string) => `/runs/session/${sessionId}`,

  // Custom Instructions
  customInstructions: "/claude-md",

  // Attachments
  attachmentsUpload: "/attachments/upload",
  audioTranscriptions: "/audio/transcriptions",

  // Environment Variables
  envVars: "/env-vars",
  envVar: (envVarId: number) => `/env-vars/${envVarId}`,

  // MCP Servers
  mcpServers: "/mcp-servers",
  mcpServer: (serverId: number) => `/mcp-servers/${serverId}`,

  // MCP Installs
  mcpInstalls: "/mcp-installs",
  mcpInstall: (installId: number) => `/mcp-installs/${installId}`,
  mcpInstallsBulk: "/mcp-installs/bulk",

  // Skills
  skills: "/skills",
  skill: (skillId: number) => `/skills/${skillId}`,
  skillFiles: (skillId: number) => `/skills/${skillId}/files`,
  skillImportDiscover: "/skills/import/discover",
  skillImportCommit: "/skills/import/commit",
  skillImportJob: (jobId: string) => `/skills/import/jobs/${jobId}`,
  skillsMarketplaceStatus: "/skills/marketplace/status",
  skillsMarketplaceSearch: "/skills/marketplace/search",
  skillsMarketplaceRecommendations: "/skills/marketplace/recommendations",
  skillsMarketplaceImportDiscover: "/skills/marketplace/import/discover",
  pendingSkillCreations: "/pending-skill-creations",
  pendingSkillCreation: (creationId: string) =>
    `/pending-skill-creations/${creationId}`,
  pendingSkillCreationConfirm: (creationId: string) =>
    `/pending-skill-creations/${creationId}/confirm`,
  pendingSkillCreationCancel: (creationId: string) =>
    `/pending-skill-creations/${creationId}/cancel`,

  // Skill Installs
  skillInstalls: "/skill-installs",
  skillInstall: (installId: number) => `/skill-installs/${installId}`,
  skillInstallsBulk: "/skill-installs/bulk",

  // Plugins
  plugins: "/plugins",
  plugin: (pluginId: number) => `/plugins/${pluginId}`,
  pluginImportDiscover: "/plugins/import/discover",
  pluginImportCommit: "/plugins/import/commit",
  pluginImportJob: (jobId: string) => `/plugins/import/jobs/${jobId}`,

  // Plugin Installs
  pluginInstalls: "/plugin-installs",
  pluginInstall: (installId: number) => `/plugin-installs/${installId}`,
  pluginInstallsBulk: "/plugin-installs/bulk",

  // Slash Commands
  slashCommands: "/slash-commands",
  slashCommandSuggestions: "/slash-commands/suggestions",
  slashCommand: (commandId: number) => `/slash-commands/${commandId}`,

  // Presets
  presets: "/presets",
  presetVisuals: "/presets/visuals",
  preset: (presetId: number) => `/presets/${presetId}`,

  // Sub Agents
  subAgents: "/subagents",
  subAgent: (subAgentId: number) => `/subagents/${subAgentId}`,

  // Callback
  callback: "/callback",
  callbackHealth: "/callback/health",

  // Scheduled Tasks
  scheduledTasks: "/scheduled-tasks",
  scheduledTask: (taskId: string) => `/scheduled-tasks/${taskId}`,
  scheduledTaskTrigger: (taskId: string) =>
    `/scheduled-tasks/${taskId}/trigger`,
  scheduledTaskRuns: (taskId: string) => `/scheduled-tasks/${taskId}/runs`,

  // Messages
  message: (messageId: number) => `/messages/${messageId}`,

  // Tool Executions
  toolExecution: (executionId: string) => `/tool-executions/${executionId}`,

  // Projects
  projects: "/projects",
  project: (projectId: string) => `/projects/${projectId}`,
  projectFiles: (projectId: string) => `/projects/${projectId}/files`,
  projectFile: (projectId: string, fileId: number) =>
    `/projects/${projectId}/files/${fileId}`,

  // Workspaces
  workspaces: "/workspaces",
  workspace: (workspaceId: string) => `/workspaces/${workspaceId}`,
  workspaceMembers: (workspaceId: string) =>
    `/workspaces/${workspaceId}/members`,
  workspaceMember: (workspaceId: string, membershipId: number) =>
    `/workspaces/${workspaceId}/members/${membershipId}`,
  workspaceMemberRole: (workspaceId: string, membershipId: number) =>
    `/workspaces/${workspaceId}/members/${membershipId}/role`,
  workspaceLeave: (workspaceId: string) =>
    `/workspaces/${workspaceId}/members/leave`,
  workspaceInvites: (workspaceId: string) =>
    `/workspaces/${workspaceId}/invites`,
  workspaceInviteRevoke: (workspaceId: string, inviteId: string) =>
    `/workspaces/${workspaceId}/invites/${inviteId}/revoke`,
  workspaceActivity: (workspaceId: string) =>
    `/workspaces/${workspaceId}/activity`,

  // Auth
  authConfig: "/auth/config",
  authMe: "/auth/me",
  authLogout: "/auth/logout",

  // Health
  health: "/health",
  root: "/",
} as const;

// ---------------------------------------------------------------------------
// Base URL resolution
// ---------------------------------------------------------------------------

const AUTH_SESSION_COOKIE_NAME =
  process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME || "poco_session";

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

/**
 * Resolve the API base URL for the current environment.
 *
 * - **Browser**: always uses the same-origin Next.js proxy.
 * - **Server**: requires `BACKEND_URL` / `POCO_BACKEND_URL` / `POCO_API_URL`
 *   for absolute backend URLs.
 */
export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "";
  }

  const serverBaseUrl =
    process.env.BACKEND_URL ||
    process.env.POCO_BACKEND_URL ||
    process.env.POCO_API_URL;

  if (!serverBaseUrl) {
    throw new ApiError(
      "API base URL is not configured (set BACKEND_URL, POCO_BACKEND_URL, or POCO_API_URL for server-side calls)",
      500,
    );
  }

  return normalizeBaseUrl(serverBaseUrl);
}

// ---------------------------------------------------------------------------
// Server-side auth session forwarding
// ---------------------------------------------------------------------------

async function resolveAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const cookieStore = await cookies();
      return cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value || null;
    } catch {
      return null;
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// Request helpers
// ---------------------------------------------------------------------------

function normalizeBody(body: unknown): BodyInit | undefined {
  if (body === undefined || body === null) return undefined;
  if (typeof body === "string" || body instanceof FormData) return body;
  return JSON.stringify(body);
}

const IS_DEV =
  typeof process !== "undefined" && process.env.NODE_ENV === "development";

function logApi(
  level: "info" | "error",
  method: string,
  endpoint: string,
  extra?: Record<string, unknown>,
): void {
  if (!IS_DEV) return;
  const color = level === "error" ? "#ef4444" : "#0ea5e9";
  const prefix = `%c[API] ${method} ${endpoint}`;
  if (extra) {
    console.log(prefix, `color: ${color}; font-weight: bold;`, extra);
  } else {
    console.log(prefix, `color: ${color}; font-weight: bold;`);
  }
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

export type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
  next?: {
    revalidate?: number;
    tags?: string[];
  };
};

/**
 * Low-level fetch wrapper that handles:
 * - Base URL resolution and endpoint prefixing
 * - Auth token injection
 * - Timeout via AbortController
 * - Unwrapping `ApiResponse<T>` envelopes
 * - Structured error handling
 */
export async function apiFetch<T>(
  endpoint: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { timeoutMs = 60_000, ...fetchOptions } = options;
  const baseUrl = getApiBaseUrl();
  const fullUrl = `${baseUrl}${API_PREFIX}${endpoint}`;
  const method = fetchOptions.method || "GET";

  logApi("info", method, endpoint);

  // Build headers
  const headers = new Headers(fetchOptions.headers);
  if (
    !headers.has("Content-Type") &&
    !(fetchOptions.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  const token = await resolveAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Timeout management
  const hasExternalSignal = Boolean(fetchOptions.signal);
  const controller = hasExternalSignal ? null : new AbortController();
  const timeoutId =
    !hasExternalSignal && timeoutMs > 0
      ? setTimeout(() => controller?.abort(), timeoutMs)
      : null;

  try {
    const response = await fetch(fullUrl, {
      ...fetchOptions,
      headers,
      credentials: fetchOptions.credentials ?? "include",
      signal: fetchOptions.signal ?? controller?.signal,
      body: normalizeBody(fetchOptions.body),
    });

    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const message =
        typeof payload === "object" && payload && "message" in payload
          ? String((payload as { message?: string }).message)
          : response.statusText;

      logApi("error", method, endpoint, {
        status: response.status,
        message,
      });

      throw new ApiError(
        message || "API request failed",
        response.status,
        payload,
      );
    }

    // Unwrap standard API envelope { code, message, data }
    if (typeof payload === "object" && payload && "data" in payload) {
      const wrapped = payload as ApiResponse<T>;
      if (wrapped.code !== 200 && wrapped.code !== 0) {
        throw new ApiError(
          wrapped.message || "API request failed",
          wrapped.code,
        );
      }
      return wrapped.data as T;
    }

    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timeout", 408);
    }
    throw error;
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Typed HTTP client
// ---------------------------------------------------------------------------

/**
 * Convenience HTTP client with typed methods for each verb.
 *
 * @example
 * ```ts
 * const sessions = await apiClient.get<Session[]>(API_ENDPOINTS.sessions);
 * await apiClient.post(API_ENDPOINTS.sessions, { prompt: "Hello" });
 * ```
 */
export const apiClient = {
  get: <T>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: "POST",
      body: body as BodyInit | null | undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body as BodyInit | null | undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body as BodyInit | null | undefined,
    }),

  delete: <T>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "DELETE" }),
};
