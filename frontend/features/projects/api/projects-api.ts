import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { SessionResponse } from "@/features/chat/types";
import { userInputService } from "@/features/chat/api/user-input-api";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";

interface ProjectApiResponse {
  project_id: string;
  user_id?: string;
  name: string;
  repo_url?: string | null;
  git_branch?: string | null;
  git_token_env_key?: string | null;
  created_at?: string;
  updated_at?: string;
  task_count?: number;
}

function mapProject(project: ProjectApiResponse): ProjectItem {
  return {
    id: project.project_id,
    name: project.name,
    userId: project.user_id,
    repoUrl: project.repo_url ?? null,
    gitBranch: project.git_branch ?? null,
    gitTokenEnvKey: project.git_token_env_key ?? null,
    createdAt: project.created_at,
    updatedAt: project.updated_at,
    taskCount:
      typeof project.task_count === "number" ? project.task_count : undefined,
  };
}

function resolveSessionTitle(session: SessionResponse): string {
  if (session.title?.trim()) {
    return session.title.trim();
  }

  const todoContent = session.state_patch?.todos?.[0]?.content;
  if (todoContent?.trim()) {
    const content = todoContent.trim();
    return content.length > 50 ? `${content.slice(0, 50)}...` : content;
  }

  // Return empty string to let UI layer handle i18n "New Chat" display
  return "";
}

function mapSessionToTask(session: SessionResponse): TaskHistoryItem {
  return {
    id: session.session_id,
    title: resolveSessionTitle(session),
    timestamp: session.updated_at || session.created_at,
    status: session.status as TaskHistoryItem["status"],
    projectId: session.project_id || undefined,
  };
}

export const projectsService = {
  listProjects: async (options?: {
    revalidate?: number;
  }): Promise<ProjectItem[]> => {
    try {
      const projects = await apiClient.get<ProjectApiResponse[]>(
        API_ENDPOINTS.projects,
        {
          next: { revalidate: options?.revalidate },
        },
      );
      return projects.map(mapProject);
    } catch (error) {
      console.warn(
        "[Projects] Failed to fetch projects, using empty list",
        error,
      );
      return [];
    }
  },

  createProject: async (payload: {
    name: string;
    repo_url?: string;
    git_branch?: string;
    git_token_env_key?: string | null;
  }): Promise<ProjectItem> => {
    const project = await apiClient.post<ProjectApiResponse>(
      API_ENDPOINTS.projects,
      payload,
    );
    return mapProject(project);
  },

  updateProject: async (
    projectId: string,
    payload: {
      name?: string;
      repo_url?: string | null;
      git_branch?: string | null;
      git_token_env_key?: string | null;
    },
  ): Promise<ProjectItem> => {
    const project = await apiClient.patch<ProjectApiResponse>(
      API_ENDPOINTS.project(projectId),
      payload,
    );
    return mapProject(project);
  },

  deleteProject: async (projectId: string): Promise<void> => {
    await apiClient.delete(API_ENDPOINTS.project(projectId));
  },
};

export const tasksService = {
  listHistory: async (options?: {
    revalidate?: number;
  }): Promise<TaskHistoryItem[]> => {
    try {
      const [sessionsResult, pendingResult] = await Promise.allSettled([
        apiClient.get<SessionResponse[]>(API_ENDPOINTS.sessions, {
          next: { revalidate: options?.revalidate },
        }),
        userInputService.listPending(),
      ]);

      if (sessionsResult.status === "rejected") {
        throw sessionsResult.reason;
      }

      const pendingRequests =
        pendingResult.status === "fulfilled" ? pendingResult.value : [];
      const now = Date.now();
      const pendingSessionIds = new Set<string>();

      for (const request of pendingRequests) {
        if (request.tool_name === "ExitPlanMode") continue;
        if (!request.session_id) continue;
        const expiresAt = request.expires_at
          ? new Date(request.expires_at).getTime()
          : 0;
        if (expiresAt > now) {
          pendingSessionIds.add(request.session_id);
        }
      }

      return sessionsResult.value.map((session) => ({
        ...mapSessionToTask(session),
        hasPendingUserInput: pendingSessionIds.has(session.session_id),
      }));
    } catch (error) {
      console.warn(
        "[Tasks] Failed to fetch task history, using empty list",
        error,
      );
      return [];
    }
  },

  updateTaskProject: async (
    sessionId: string,
    projectId: string | null,
  ): Promise<void> => {
    await apiClient.patch(API_ENDPOINTS.session(sessionId), {
      project_id: projectId,
    });
  },
};
