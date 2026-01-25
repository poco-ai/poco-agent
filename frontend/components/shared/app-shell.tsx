"use client";

import * as React from "react";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/shared/sidebar/app-sidebar";
import { SettingsDialog } from "@/features/settings/components/settings-dialog";

import { useProjects } from "@/features/projects/hooks/use-projects";
import { useTaskHistory } from "@/features/projects/hooks/use-task-history";
import { useProjectDeletion } from "@/features/projects/hooks/use-project-deletion";

import { TaskHistoryProvider } from "@/features/projects/contexts/task-history-context";
import { AppShellProvider } from "@/components/shared/app-shell-context";

export function AppShell({
  lng,
  children,
}: {
  lng: string;
  children: React.ReactNode;
}) {
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);

  const { projects, addProject, updateProject, removeProject } = useProjects(
    {},
  );
  const { taskHistory, addTask, removeTask, moveTask, refreshTasks } =
    useTaskHistory({});

  const deleteProject = useProjectDeletion({
    taskHistory,
    moveTask,
    removeProject,
  });

  const openSettings = React.useCallback(() => {
    setIsSettingsOpen(true);
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
    <TaskHistoryProvider value={{ refreshTasks }}>
      <AppShellProvider value={contextValue}>
        <SidebarProvider defaultOpen={true}>
          <div className="flex h-screen w-full overflow-hidden bg-background">
            <AppSidebar
              projects={projects}
              taskHistory={taskHistory}
              onDeleteTask={removeTask}
              onMoveTaskToProject={moveTask}
              onCreateProject={addProject}
              onRenameProject={handleRenameProject}
              onDeleteProject={handleDeleteProject}
              onOpenSettings={openSettings}
            />

            <SidebarInset className="flex flex-col bg-muted/30 min-h-0">
              {children}
            </SidebarInset>

            <SettingsDialog
              open={isSettingsOpen}
              onOpenChange={setIsSettingsOpen}
            />
          </div>
        </SidebarProvider>
      </AppShellProvider>
    </TaskHistoryProvider>
  );
}
