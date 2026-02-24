"use client";

import * as React from "react";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./sidebar/app-sidebar";
import { SettingsDialog } from "@/features/settings";

import {
  TaskHistoryProvider,
  useProjectDeletion,
  useProjects,
  useTaskHistory,
} from "@/features/projects";

import { AppShellProvider } from "./app-shell-context";
import { OnboardingTour, useOnboardingTour } from "@/features/onboarding";
import { useSettingsShortcut } from "./hooks/use-settings-shortcut";
import { useProjectActions } from "./hooks/use-project-actions";

export function AppShell({
  lng,
  children,
}: {
  lng: string;
  children: React.ReactNode;
}) {
  const {
    isSettingsOpen,
    settingsTabRequest,
    openSettings,
    handleSettingsOpenChange,
  } = useSettingsShortcut();

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

  const { handleRenameProject, handleDeleteProject } = useProjectActions({
    updateProject,
    deleteProject,
  });

  const onboarding = useOnboardingTour();

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
