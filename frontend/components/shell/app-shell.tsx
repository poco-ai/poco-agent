"use client";

import * as React from "react";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./sidebar/app-sidebar";
import {
  SettingsDialog,
  type SettingsTabId,
  type SettingsTabRequest,
} from "@/features/settings";

import {
  TaskHistoryProvider,
  useProjectDeletion,
  useProjects,
  useTaskHistory,
} from "@/features/projects";

import { AppShellProvider } from "./app-shell-context";
import { OnboardingTour, useOnboardingTour } from "@/features/onboarding";

export function AppShell({
  lng,
  children,
}: {
  lng: string;
  children: React.ReactNode;
}) {
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [settingsTabRequest, setSettingsTabRequest] =
    React.useState<SettingsTabRequest | null>(null);

  const { projects, addProject, updateProject, removeProject } = useProjects(
    {},
  );
  const {
    taskHistory,
    addTask,
    touchTask,
    removeTask,
    moveTask,
    renameTask,
    refreshTasks,
  } = useTaskHistory({});

  const deleteProject = useProjectDeletion({
    taskHistory,
    moveTask,
    removeProject,
  });
  const onboarding = useOnboardingTour();

  const openSettings = React.useCallback((tab?: SettingsTabId) => {
    if (tab) {
      setSettingsTabRequest({ tab, requestId: Date.now() });
    } else {
      setSettingsTabRequest(null);
    }
    setIsSettingsOpen(true);
  }, []);

  const toggleSettingsByHotkey = React.useCallback(() => {
    setIsSettingsOpen((prev) => {
      const next = !prev;
      if (!next) {
        setSettingsTabRequest(null);
      }
      return next;
    });
  }, []);

  React.useEffect(() => {
    const handleOpenSettingsShortcut = (event: KeyboardEvent) => {
      if (!event.ctrlKey) return;
      if (!(event.key === "," || event.code === "Comma")) return;
      event.preventDefault();
      event.stopPropagation();
      toggleSettingsByHotkey();
    };

    window.addEventListener("keydown", handleOpenSettingsShortcut, true);
    return () => {
      window.removeEventListener("keydown", handleOpenSettingsShortcut, true);
    };
  }, [toggleSettingsByHotkey]);

  const handleSettingsOpenChange = React.useCallback((nextOpen: boolean) => {
    setIsSettingsOpen(nextOpen);
    if (!nextOpen) {
      setSettingsTabRequest(null);
    }
  }, []);

  const handleRenameProject = React.useCallback(
    (projectId: string, newName: string) => {
      updateProject(projectId, { name: newName });
    },
    [updateProject],
  );

  const handleDeleteProject = React.useCallback(
    async (projectId: string) => {
      await deleteProject(projectId);
    },
    [deleteProject],
  );

  const contextValue = React.useMemo(
    () => ({
      lng,
      openSettings,

      projects,
      addProject,
      updateProject,
      deleteProject: handleDeleteProject,

      taskHistory,
      addTask,
      removeTask,
      moveTask,
      refreshTasks,
    }),
    [
      lng,
      openSettings,
      projects,
      addProject,
      updateProject,
      handleDeleteProject,
      taskHistory,
      addTask,
      removeTask,
      moveTask,
      refreshTasks,
    ],
  );

  return (
    <TaskHistoryProvider value={{ refreshTasks, touchTask }}>
      <AppShellProvider value={contextValue}>
        <SidebarProvider defaultOpen={true}>
          <div
            className="flex h-dvh w-full overflow-hidden bg-background"
            data-onboarding="workspace-main"
          >
            <AppSidebar
              projects={projects}
              taskHistory={taskHistory}
              onDeleteTask={removeTask}
              onRenameTask={renameTask}
              onMoveTaskToProject={moveTask}
              onCreateProject={addProject}
              onRenameProject={handleRenameProject}
              onDeleteProject={handleDeleteProject}
              onOpenSettings={openSettings}
              onStartOnboarding={onboarding.startTour}
            />

            <SidebarInset className="flex flex-col bg-muted/30 min-h-0">
              {children}
            </SidebarInset>

            <SettingsDialog
              open={isSettingsOpen}
              onOpenChange={handleSettingsOpenChange}
              tabRequest={settingsTabRequest ?? undefined}
              onStartOnboarding={onboarding.startTour}
            />

            <OnboardingTour
              open={onboarding.isOpen}
              runId={onboarding.runId}
              lng={lng}
              onClose={onboarding.closeTour}
            />
          </div>
        </SidebarProvider>
      </AppShellProvider>
    </TaskHistoryProvider>
  );
}
