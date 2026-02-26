export interface ProjectItem {
  id: string;
  name: string;
  icon?: string;
  /** Default git repository context (GitHub-only in v1). */
  repoUrl?: string | null;
  gitBranch?: string | null;
  /** Env var key holding a GitHub token (e.g. "GITHUB_TOKEN"). */
  gitTokenEnvKey?: string | null;
  /** Number of tasks under this project, if the API returns it */
  taskCount?: number;
  /** Optional text summary shown in the header */
  description?: string | null;
  /** Owning user identifier */
  userId?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface TaskHistoryItem {
  id: string;
  title: string;
  timestamp: string;
  status: "pending" | "running" | "completed" | "failed" | "canceled";
  projectId?: string;
  hasPendingUserInput?: boolean;
}

export interface AddTaskOptions {
  timestamp?: string;
  status?: TaskHistoryItem["status"];
  projectId?: string;
  id?: string;
}
