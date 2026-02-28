import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  SearchResultMessage,
  SearchResultProject,
  SearchResultTask,
} from "@/features/search/types";

type SearchTaskApi = {
  session_id: string;
  title: string | null;
  status: string;
  timestamp: string;
};

type SearchProjectApi = {
  project_id: string;
  name: string;
};

type SearchMessageApi = {
  message_id: number;
  session_id: string;
  text_preview: string;
  timestamp: string;
};

type GlobalSearchApiResponse = {
  query: string;
  tasks: SearchTaskApi[];
  projects: SearchProjectApi[];
  messages: SearchMessageApi[];
};

function mapTask(task: SearchTaskApi): SearchResultTask {
  return {
    id: task.session_id,
    title: task.title ?? "",
    status: task.status,
    timestamp: task.timestamp,
    type: "task",
  };
}

function mapProject(project: SearchProjectApi): SearchResultProject {
  return {
    id: project.project_id,
    name: project.name,
    type: "project",
  };
}

function mapMessage(message: SearchMessageApi): SearchResultMessage {
  return {
    id: message.message_id,
    content: message.text_preview,
    chatId: message.session_id,
    timestamp: message.timestamp,
    type: "message",
  };
}

function buildQuery(
  params: Record<string, string | number | undefined | null>,
) {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    sp.set(key, String(value));
  }
  const query = sp.toString();
  return query ? `?${query}` : "";
}

export const searchService = {
  globalSearch: async (
    params: {
      q: string;
      limit_tasks?: number;
      limit_projects?: number;
      limit_messages?: number;
      project_id?: string | null;
    },
    options?: { signal?: AbortSignal },
  ): Promise<{
    tasks: SearchResultTask[];
    projects: SearchResultProject[];
    messages: SearchResultMessage[];
  }> => {
    const query = buildQuery(params);
    const data = await apiClient.get<GlobalSearchApiResponse>(
      `${API_ENDPOINTS.search}${query}`,
      { signal: options?.signal },
    );

    return {
      tasks: (data.tasks ?? []).map(mapTask),
      projects: (data.projects ?? []).map(mapProject),
      messages: (data.messages ?? []).map(mapMessage),
    };
  },
};
