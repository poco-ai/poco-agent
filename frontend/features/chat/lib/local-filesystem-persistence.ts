import type { LocalFilesystemDraft } from "@/features/task-composer/types";
import type {
  LocalMountConfig,
  SessionUpdateRequest,
} from "@/features/chat/types";

interface PersistSessionLocalFilesystemArgs<TProjectResult = unknown> {
  sessionId: string;
  projectId?: string | null;
  draft: LocalFilesystemDraft;
  persistSession: (
    sessionId: string,
    payload: SessionUpdateRequest,
  ) => Promise<unknown>;
  persistProject?: (
    projectId: string,
    payload: { local_mounts: LocalMountConfig[] },
  ) => Promise<TProjectResult>;
}

export async function persistSessionLocalFilesystem<TProjectResult = unknown>({
  sessionId,
  projectId,
  draft,
  persistSession,
  persistProject,
}: PersistSessionLocalFilesystemArgs<TProjectResult>): Promise<TProjectResult | null> {
  await persistSession(sessionId, {
    config: {
      filesystem_mode: draft.filesystem_mode,
      local_mounts: draft.local_mounts,
    },
  });

  if (!projectId || !persistProject) {
    return null;
  }

  return persistProject(projectId, {
    local_mounts: draft.local_mounts,
  });
}
