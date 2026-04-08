import type { LocalMountConfig } from "@/features/chat/types/api/session";

export interface ProjectItem {
  id: string;
  name: string;
  icon?: string;
  defaultModel?: string | null;
  defaultPresetId?: number | null;
  localMounts?: LocalMountConfig[];
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

export interface ProjectFile {
  id: number;
  projectId: string;
  fileName: string;
  fileSource: string;
  fileSize?: number | null;
  fileContentType?: string | null;
  sortOrder: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface TaskHistoryItem {
  id: string;
  title: string;
  timestamp: string;
  status:
    | "pending"
    | "running"
    | "canceling"
    | "completed"
    | "failed"
    | "canceled";
  projectId?: string;
  isPinned?: boolean;
  pinnedAt?: string | null;
  hasPendingUserInput?: boolean;
}

export interface AddTaskOptions {
  timestamp?: string;
  status?: TaskHistoryItem["status"];
  projectId?: string;
  id?: string;
}
