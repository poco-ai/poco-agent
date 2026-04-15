"use client";

import * as React from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { workspacesApi } from "@/features/workspaces/api/workspaces-api";
import type { Workspace } from "@/features/workspaces/model/types";

const SELECTED_WORKSPACE_STORAGE_KEY = "poco.selectedWorkspaceId";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  currentWorkspaceId: string | null;
  isLoading: boolean;
  refreshWorkspaces: () => Promise<void>;
  selectWorkspace: (workspaceId: string) => void;
  createWorkspace: (name: string) => Promise<Workspace | null>;
}

const WorkspaceContext = React.createContext<WorkspaceContextValue | null>(null);

function pickWorkspace(
  workspaces: Workspace[],
  preferredWorkspaceId: string | null,
): Workspace | null {
  if (workspaces.length === 0) return null;
  if (preferredWorkspaceId) {
    const preferred = workspaces.find((item) => item.id === preferredWorkspaceId);
    if (preferred) return preferred;
  }
  return (
    workspaces.find((item) => item.kind === "shared") ??
    workspaces.find((item) => item.kind === "personal") ??
    workspaces[0]
  );
}

export function WorkspaceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { t } = useT("translation");
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [currentWorkspaceId, setCurrentWorkspaceId] = React.useState<
    string | null
  >(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const selectWorkspace = React.useCallback((workspaceId: string) => {
    setCurrentWorkspaceId(workspaceId);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SELECTED_WORKSPACE_STORAGE_KEY, workspaceId);
    }
  }, []);

  const refreshWorkspaces = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const nextWorkspaces = await workspacesApi.listWorkspaces();
      setWorkspaces(nextWorkspaces);

      const storedWorkspaceId =
        typeof window !== "undefined"
          ? window.localStorage.getItem(SELECTED_WORKSPACE_STORAGE_KEY)
          : null;
      const selected = pickWorkspace(
        nextWorkspaces,
        currentWorkspaceId ?? storedWorkspaceId,
      );
      if (selected) {
        setCurrentWorkspaceId(selected.id);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(SELECTED_WORKSPACE_STORAGE_KEY, selected.id);
        }
      }
    } catch (error) {
      console.error("[Workspaces] list failed", error);
      toast.error(t("workspaces.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkspaceId, t]);

  React.useEffect(() => {
    void refreshWorkspaces();
  }, [refreshWorkspaces]);

  const createWorkspace = React.useCallback(
    async (name: string): Promise<Workspace | null> => {
      const trimmedName = name.trim();
      if (!trimmedName) return null;

      try {
        const created = await workspacesApi.createWorkspace(trimmedName);
        setWorkspaces((prev) => [created, ...prev]);
        selectWorkspace(created.id);
        toast.success(t("workspaces.toasts.created"));
        return created;
      } catch (error) {
        console.error("[Workspaces] create failed", error);
        toast.error(t("workspaces.toasts.createFailed"));
        return null;
      }
    },
    [selectWorkspace, t],
  );

  const currentWorkspace = pickWorkspace(workspaces, currentWorkspaceId);

  const value = React.useMemo(
    () => ({
      workspaces,
      currentWorkspace,
      currentWorkspaceId: currentWorkspace?.id ?? currentWorkspaceId,
      isLoading,
      refreshWorkspaces,
      selectWorkspace,
      createWorkspace,
    }),
    [
      workspaces,
      currentWorkspace,
      currentWorkspaceId,
      isLoading,
      refreshWorkspaces,
      selectWorkspace,
      createWorkspace,
    ],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspaceContext(): WorkspaceContextValue {
  const value = React.useContext(WorkspaceContext);
  if (!value) {
    throw new Error("useWorkspaceContext must be used within WorkspaceProvider");
  }
  return value;
}
