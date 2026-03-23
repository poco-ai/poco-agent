import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { chatService } from "@/features/chat/api/chat-api";
import type { FileNode } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

export type ViewMode = "artifacts" | "document";

const normalizePath = (value: string) => value.replace(/^\/+/, "");

const PRESIGNED_URL_REFRESH_BUFFER_MS = 30_000;

const ensureUrl = (value?: string | null) => {
  if (!value) return null;
  try {
    return new URL(
      value,
      typeof window !== "undefined" ? window.location.origin : undefined,
    );
  } catch {
    return null;
  }
};

const parseAmzDate = (value: string): number | null => {
  const match = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(value);
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match;
  return Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second),
  );
};

const getPresignedUrlExpiresAt = (rawUrl?: string | null): number | null => {
  const url = ensureUrl(rawUrl);
  if (!url) return null;
  const params = url.searchParams;

  const amzDate =
    params.get("X-Amz-Date") ?? params.get("x-amz-date") ?? undefined;
  const amzExpires =
    params.get("X-Amz-Expires") ?? params.get("x-amz-expires") ?? undefined;

  if (amzDate && amzExpires) {
    const baseMs = parseAmzDate(amzDate);
    const expiresSec = Number(amzExpires);
    if (baseMs && Number.isFinite(expiresSec) && expiresSec >= 0) {
      return baseMs + expiresSec * 1000;
    }
  }

  const legacyExpires =
    params.get("Expires") ?? params.get("expires") ?? undefined;
  if (legacyExpires) {
    const epochSec = Number(legacyExpires);
    if (Number.isFinite(epochSec) && epochSec > 0) return epochSec * 1000;
  }

  return null;
};

const isActiveStatus = (status?: UseArtifactsOptions["sessionStatus"]) =>
  status === "running" || status === "pending";

const isFinishedStatus = (status?: UseArtifactsOptions["sessionStatus"]) =>
  status === "completed" || status === "failed" || status === "canceled";

const findFileByPath = (
  nodes: FileNode[],
  targetPath: string,
): FileNode | undefined => {
  const normalizedTarget = normalizePath(targetPath);
  for (const node of nodes) {
    if (node.type === "file" && normalizePath(node.path) === normalizedTarget) {
      return node;
    }
    if (node.children && node.children.length) {
      const found = findFileByPath(node.children, targetPath);
      if (found) return found;
    }
  }
  return undefined;
};

interface UseArtifactsOptions {
  sessionId?: string;
  sessionStatus?: "pending" | "running" | "completed" | "failed" | "canceled";
}

interface UseArtifactsReturn {
  files: FileNode[];
  selectedFile: FileNode | undefined;
  viewMode: ViewMode;
  isRefreshing: boolean;
  selectFile: (file: FileNode) => void;
  closeViewer: () => void;
  refreshFiles: () => Promise<void>;
  ensureFreshFile: (file: FileNode) => Promise<FileNode | undefined>;
}

/**
 * Manages artifacts panel state and file list fetching
 *
 * Responsibilities:
 * - Fetch workspace file list from API
 * - Auto-refresh when session finishes
 * - Manage view mode (artifacts list vs document preview)
 * - Manage sidebar open/close state
 * - Handle file selection
 * - Force open sidebar for file preview
 */
export function useArtifacts({
  sessionId,
  sessionStatus,
}: UseArtifactsOptions): UseArtifactsReturn {
  const { t } = useT("translation");
  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | undefined>();
  const [viewMode, setViewMode] = useState<ViewMode>("artifacts");
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Coalesce concurrent refresh triggers (manual / auto / polling) into one request.
  const fetchPromiseRef = useRef<Promise<FileNode[]> | null>(null);
  const fetchFiles = useCallback(async (): Promise<FileNode[]> => {
    if (!sessionId) return [];
    if (fetchPromiseRef.current) return fetchPromiseRef.current;

    const promise = (async () => {
      setIsRefreshing(true);
      try {
        const session = await chatService.getSessionRaw(sessionId);
        const workspaceFiles = await chatService.getFiles(sessionId);
        const filesystemMode =
          session.config_snapshot?.filesystem_mode === "local_mount"
            ? "local_mount"
            : "sandbox";
        const localMountFiles =
          filesystemMode === "local_mount"
            ? await chatService.getLocalMountFiles(sessionId)
            : [];

        const data =
          filesystemMode === "local_mount"
            ? [
                {
                  id: "__workspace_root__",
                  name: t("fileSidebar.workspaceRoot"),
                  path: "__workspace_root__",
                  type: "folder" as const,
                  children: workspaceFiles,
                },
                {
                  id: "__local_mounts_root__",
                  name: t("fileSidebar.localMountsRoot"),
                  path: "__local_mounts_root__",
                  type: "folder" as const,
                  children: localMountFiles,
                },
              ]
            : workspaceFiles;
        setFiles(data);
        return data;
      } catch (error) {
        console.error("[Artifacts] Failed to fetch workspace files:", error);
        return [];
      } finally {
        setIsRefreshing(false);
        fetchPromiseRef.current = null;
      }
    })();

    fetchPromiseRef.current = promise;
    return promise;
  }, [sessionId, t]);

  // Manual refresh method
  const refreshFiles = useCallback(async () => {
    await fetchFiles();
  }, [fetchFiles]);

  const ensureFreshFile = useCallback(
    async (file: FileNode): Promise<FileNode | undefined> => {
      if (!sessionId) return file;

      const maybeRefresh = (() => {
        if (!file.url) return true;
        const expiresAt = getPresignedUrlExpiresAt(file.url);
        if (!expiresAt) return false;
        return expiresAt - Date.now() <= PRESIGNED_URL_REFRESH_BUFFER_MS;
      })();

      if (!maybeRefresh) return file;

      try {
        const updated = await fetchFiles();
        return findFileByPath(updated, file.path) ?? file;
      } catch {
        return file;
      }
    },
    [sessionId, fetchFiles],
  );

  // Initial fetch when sessionId becomes available.
  useEffect(() => {
    setViewMode("artifacts");
    setSelectedPath(undefined);
    void fetchFiles();
  }, [sessionId, fetchFiles]);

  // Auto-refresh when session transitions into a finished status.
  const prevStatusRef = useRef<typeof sessionStatus>(undefined);
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = sessionStatus;

    if (!sessionId || !sessionStatus) return;
    if (isActiveStatus(prevStatus) && isFinishedStatus(sessionStatus)) {
      void fetchFiles();
    }
  }, [sessionId, sessionStatus, fetchFiles]);

  // Select a file and switch to document view
  const selectFile = useCallback((file: FileNode) => {
    setSelectedPath(normalizePath(file.path));
    setViewMode("document");
  }, []);

  const closeViewer = useCallback(() => {
    setViewMode("artifacts");
    setSelectedPath(undefined);
  }, []);

  const selectedFile = useMemo((): FileNode | undefined => {
    if (!selectedPath) return undefined;
    return (
      findFileByPath(files, selectedPath) ?? {
        id: selectedPath,
        name: selectedPath.split("/").pop() || selectedPath,
        path: selectedPath,
        type: "file",
      }
    );
  }, [files, selectedPath]);

  // If the selected file URL is expired/expiring, refresh once so the viewer gets a fresh presigned URL.
  const lastExpiryRefreshAtRef = useRef(0);
  useEffect(() => {
    if (!sessionId) return;
    if (viewMode !== "document") return;
    if (!selectedFile) return;
    if (!selectedFile.url) return;

    const expiresAt = getPresignedUrlExpiresAt(selectedFile.url);
    if (!expiresAt) return;
    if (expiresAt - Date.now() > PRESIGNED_URL_REFRESH_BUFFER_MS) return;

    const now = Date.now();
    if (now - lastExpiryRefreshAtRef.current < 2000) return;
    lastExpiryRefreshAtRef.current = now;

    void fetchFiles();
  }, [sessionId, viewMode, selectedFile, fetchFiles]);

  // If the user opens a file before its preview URL is ready, poll until it becomes available.
  useEffect(() => {
    if (!sessionId) return;
    if (viewMode !== "document") return;
    if (!selectedPath) return;
    if (selectedFile?.url) return;

    const intervalMs = 2000;
    const maxAttempts = 60; // ~2 minutes
    let attempts = 0;
    let cancelled = false;
    let timer: number | undefined;

    const pollOnce = async () => {
      if (cancelled) return;
      if (attempts >= maxAttempts) return;
      attempts += 1;
      await fetchFiles();
      if (cancelled) return;
      timer = window.setTimeout(() => {
        void pollOnce();
      }, intervalMs);
    };

    // Kick off immediately so the preview can become available ASAP.
    void pollOnce();

    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [sessionId, viewMode, selectedPath, selectedFile?.url, fetchFiles]);

  // Listen for close-document-viewer event
  useEffect(() => {
    const handleCloseViewer = () => {
      closeViewer();
    };

    window.addEventListener("close-document-viewer", handleCloseViewer);
    return () => {
      window.removeEventListener("close-document-viewer", handleCloseViewer);
    };
  }, [closeViewer]);

  return {
    files,
    selectedFile,
    viewMode,
    isRefreshing,
    selectFile,
    closeViewer,
    refreshFiles,
    ensureFreshFile,
  };
}
