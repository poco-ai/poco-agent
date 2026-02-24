"use client";

import * as React from "react";

import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import type { SettingsTabId } from "@/features/settings/types";

export type AddTaskOptions = {
  timestamp?: string;
  status?: TaskHistoryItem["status"];
  projectId?: string;
  id?: string;
};

export type ProjectRepoDefaultsInput = {
  repo_url?: string | null;
  git_branch?: string | null;
  git_token_env_key?: string | null;
};

export type ProjectUpdatesInput = {
  name?: string;
} & ProjectRepoDefaultsInput;

export interface AppShellContextValue {
  lng: string;
  openSettings: (tab?: SettingsTabId) => void;

  projects: ProjectItem[];
  addProject: (
    name: string,
    options?: ProjectRepoDefaultsInput,
  ) => Promise<ProjectItem | null>;
  updateProject: (
    projectId: string,
    updates: ProjectUpdatesInput,
  ) => Promise<ProjectItem | null>;
  deleteProject: (projectId: string) => Promise<void>;

  taskHistory: TaskHistoryItem[];
  addTask: (title: string, options?: AddTaskOptions) => TaskHistoryItem;
  removeTask: (taskId: string) => Promise<void>;
  moveTask: (taskId: string, projectId: string | null) => Promise<void>;
  refreshTasks: () => Promise<void>;
}

const AppShellContext = React.createContext<AppShellContextValue | null>(null);

export function AppShellProvider({
  value,
  children,
}: {
  value: AppShellContextValue;
  children: React.ReactNode;
}) {
  return (
    <AppShellContext.Provider value={value}>
      {children}
    </AppShellContext.Provider>
  );
}

export function useAppShell() {
  const context = React.useContext(AppShellContext);
  if (!context) {
    throw new Error("useAppShell must be used within AppShellProvider");
  }
  return context;
}
