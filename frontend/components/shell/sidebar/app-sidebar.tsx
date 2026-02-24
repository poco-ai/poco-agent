"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { GlobalSearchDialog, useSearchDialog } from "@/features/search";
import {
  CreateProjectDialog,
  type ProjectItem,
  type TaskHistoryItem,
} from "@/features/projects";
import { MainSidebar } from "./main-sidebar";
import type { SettingsTabId } from "@/features/settings";

interface AppSidebarProps {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  onNewTask?: () => void;
  onDeleteTask?: (taskId: string) => Promise<void> | void;
  onRenameTask?: (taskId: string, newName: string) => Promise<void> | void;
  onMoveTaskToProject?: (taskId: string, projectId: string | null) => void;
  onCreateProject?: (name: string) => void;
  onRenameProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
  onOpenSettings?: (tab?: SettingsTabId) => void;
  onStartOnboarding?: () => void;
}

// Default no-op handler
const noop = () => {};

/**
 * Unified sidebar wrapper.
 *
 * Automatically adapts behavior based on the current route to keep the sidebar
 * consistent across pages.
 */
export function AppSidebar({
  projects,
  taskHistory,
  onNewTask,
  onDeleteTask,
  onRenameTask,
  onMoveTaskToProject,
  onCreateProject,
  onRenameProject,
  onDeleteProject,
  onOpenSettings,
  onStartOnboarding,
}: AppSidebarProps) {
  const router = useRouter();
  const params = useParams();
  const { isSearchOpen, setIsSearchOpen } = useSearchDialog();
  const [isCreateProjectDialogOpen, setIsCreateProjectDialogOpen] =
    React.useState(false);

  const lng = React.useMemo(() => {
    const value = params?.lng;
    if (!value) return undefined;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

  // New task handling
  const handleNewTask = React.useCallback(() => {
    // Default behavior for pages without an explicit handler
    if (onNewTask) {
      onNewTask();
    } else {
      // Prefer keeping current language when we're under /[lng]/...
      router.push(lng ? `/${lng}/home` : "/");
    }
  }, [router, onNewTask, lng]);

  // Project creation handling
  const handleCreateProject = React.useCallback(
    (name: string) => {
      onCreateProject?.(name);
    },
    [onCreateProject],
  );

  return (
    <>
      <MainSidebar
        projects={projects}
        taskHistory={taskHistory}
        onNewTask={handleNewTask}
        onDeleteTask={onDeleteTask ?? noop}
        onRenameTask={onRenameTask}
        onMoveTaskToProject={onMoveTaskToProject}
        onRenameProject={onRenameProject}
        onDeleteProject={onDeleteProject}
        onOpenSettings={onOpenSettings}
        onStartOnboarding={onStartOnboarding}
        onOpenCreateProjectDialog={() => setIsCreateProjectDialogOpen(true)}
      />

      {/* Global Search Dialog */}
      <GlobalSearchDialog open={isSearchOpen} onOpenChange={setIsSearchOpen} />

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={isCreateProjectDialogOpen}
        onOpenChange={setIsCreateProjectDialogOpen}
        onCreateProject={handleCreateProject}
      />
    </>
  );
}
