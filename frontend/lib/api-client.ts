import { ApiError } from "./errors";
import type { ApiResponse } from "@/types";

export const API_PREFIX = "/api/v1";

export const API_ENDPOINTS = {
  // Sessions
  sessions: "/sessions",
  sessionsWithTitles: "/sessions/list-with-titles",
  session: (sessionId: string) => `/sessions/${sessionId}`,
  sessionCancel: (sessionId: string) => `/sessions/${sessionId}/cancel`,
  sessionState: (sessionId: string) => `/sessions/${sessionId}/state`,
  sessionMessages: (sessionId: string) => `/sessions/${sessionId}/messages`,
  sessionMessagesWithFiles: (sessionId: string) =>
    `/sessions/${sessionId}/messages-with-files`,
  sessionToolExecutions: (sessionId: string) =>
    `/sessions/${sessionId}/tool-executions`,
  sessionBrowserScreenshot: (sessionId: string, toolUseId: string) =>
    `/sessions/${sessionId}/computer/browser/${toolUseId}`,
  sessionUsage: (sessionId: string) => `/sessions/${sessionId}/usage`,
  sessionWorkspaceFiles: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/files`,
  sessionWorkspaceArchive: (sessionId: string) =>
    `/sessions/${sessionId}/workspace/archive`,

  // User Input Requests (AskUserQuestion)
  userInputRequests: "/user-input-requests",
  userInputRequest: (requestId: string) => `/user-input-requests/${requestId}`,
  userInputAnswer: (requestId: string) =>
    `/user-input-requests/${requestId}/answer`,

  // Tasks
  tasks: "/tasks",

  // Runs
  runsBySession: (sessionId: string) => `/runs/session/${sessionId}`,

  // User-level persistent custom instructions
  customInstructions: "/claude-md",

  // Attachments
  attachmentsUpload: "/attachments/upload",

  // Environment Variables
  envVars: "/env-vars",
  envVar: (envVarId: number) => `/env-vars/${envVarId}`,

  // MCP Servers
  mcpServers: "/mcp-servers",
  mcpServer: (serverId: number) => `/mcp-servers/${serverId}`,

  // MCP Installs (User)
  mcpInstalls: "/mcp-installs",
  mcpInstall: (installId: number) => `/mcp-installs/${installId}`,
  mcpInstallsBulk: "/mcp-installs/bulk",

  // Skills
  skills: "/skills",
  skill: (skillId: number) => `/skills/${skillId}`,
  skillImportDiscover: "/skills/import/discover",
  skillImportCommit: "/skills/import/commit",
  skillImportJob: (jobId: string) => `/skills/import/jobs/${jobId}`,

  // Skill Installs (User)
  skillInstalls: "/skill-installs",
  skillInstall: (installId: number) => `/skill-installs/${installId}`,
  skillInstallsBulk: "/skill-installs/bulk",

  // Slash Commands
  slashCommands: "/slash-commands",
  slashCommand: (commandId: number) => `/slash-commands/${commandId}`,

  // Sub Agents
  subAgents: "/subagents",
  subAgent: (subAgentId: number) => `/subagents/${subAgentId}`,

  // Callback
  callback: "/callback",
  callbackHealth: "/callback/health",

  // Schedules
  schedules: "/schedules",

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

  // Other
  projects: "/projects",
  project: (projectId: string) => `/projects/${projectId}`,
  health: "/health",
  root: "/",
};

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
}

export function getApiBaseUrl() {
  // Browser: prefer an explicit public API URL (build-time), otherwise use same-origin proxy.
  if (typeof window !== "undefined") {
    if (!API_BASE_URL) return "";
    return normalizeBaseUrl(API_BASE_URL);
  }

  // Server: relative URLs are not supported by Node.js fetch. Prefer a runtime internal URL.
  const serverBaseUrl =
    process.env.BACKEND_URL || process.env.POCO_BACKEND_URL || API_BASE_URL;
  if (!serverBaseUrl) {
    throw new ApiError(
      "API base URL is not configured (set BACKEND_URL for server-side calls)",
      500,
    );
  }
  return normalizeBaseUrl(serverBaseUrl);
}

async function resolveAuthToken(): Promise<string | null> {
  // TODO: add token support
  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const cookieStore = await cookies();
      return (
        cookieStore.get("access_token")?.value ||
        cookieStore.get("token")?.value ||
        null
      );
    } catch {
      return null;
    }
  }

  if (typeof window === "undefined") {
    return null;
  }

  try {
    return (
      window.localStorage.getItem("access_token") ||
      window.localStorage.getItem("token") ||
      null
    );
  } catch {
    return null;
  }
}

function normalizeBody(body: unknown): BodyInit | undefined {
  if (body === undefined || body === null) return undefined;
  if (typeof body === "string" || body instanceof FormData) return body;
  return JSON.stringify(body);
}

export type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
  next?: {
    revalidate?: number;
    tags?: string[];
  };
};

export async function apiFetch<T>(
  endpoint: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { timeoutMs = 60_000, ...fetchOptions } = options;
  const baseUrl = getApiBaseUrl();
  const fullUrl = `${baseUrl}${API_PREFIX}${endpoint}`;

  console.log(
    `%c[API] ${options.method || "GET"} ${endpoint}`,
    "color: #0ea5e9; font-weight: bold;",
  );

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

      console.log(
        `%c[API] Error ${endpoint}`,
        "color: #ef4444; font-weight: bold;",
        { status: response.status, message, payload },
      );

      throw new ApiError(
        message || "API request failed",
        response.status,
        payload,
      );
    }

    console.log(
      `%c[API] Success ${endpoint}`,
      "color: #22c55e; font-weight: bold;",
      payload,
    );

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
    const errorName =
      typeof error === "object" && error && "name" in error
        ? String((error as { name?: unknown }).name)
        : "";
    if (errorName === "AbortError") {
      throw new ApiError("Request timeout", 408);
    }
    throw error;
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

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
