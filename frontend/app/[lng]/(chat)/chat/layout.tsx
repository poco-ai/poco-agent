"use client";

import * as React from "react";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { LanguageProvider } from "@/app/[lng]/language-provider";
import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { useT } from "@/app/i18n/client";
import {
  createMockProjects,
  createMockTaskHistory,
} from "@/app/[lng]/home/model/mocks";
import type {
  ProjectItem,
  TaskHistoryItem,
} from "@/app/[lng]/home/model/types";

import { useRouter } from "next/navigation";
import { SettingsDialog } from "@/components/settings/settings-dialog";

export function ChatLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lng: string }>;
}) {
  const { t } = useT("translation");
  const router = useRouter();
  const [lng, setLng] = React.useState<string>("zh");
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
  const [projects, setProjects] = React.useState<ProjectItem[]>(() =>
    createMockProjects(t),
  );
  const [taskHistory, setTaskHistory] = React.useState<TaskHistoryItem[]>(() =>
    createMockTaskHistory(t),
  );

  React.useEffect(() => {
    params.then((p) => setLng(p.lng));
  }, [params]);

  const handleNewTask = React.useCallback(() => {
    // Navigate to home for new task
    router.push("/");
  }, [router]);

  const handleDeleteTask = React.useCallback((taskId: string) => {
    setTaskHistory((prev) => prev.filter((t) => t.id !== taskId));
  }, []);

  const handleCreateProject = React.useCallback((name: string) => {
    setProjects((prev) => [
      ...prev,
      {
        id: `project-${Date.now()}`,
        name,
        taskCount: 0,
        icon: "📁",
      },
    ]);
  }, []);

  const handleMoveTaskToProject = React.useCallback(
    (taskId: string, projectId: string | null) => {
      setTaskHistory((prev) =>
        prev.map((task) =>
          task.id === taskId ? { ...task, projectId } : task,
        ),
      );
    },
    [],
  );

  return (
    <LanguageProvider lng={lng}>
      <SidebarProvider defaultOpen={true}>
        <div className="flex min-h-svh w-full overflow-hidden bg-background">
          <AppSidebar
            projects={projects}
            taskHistory={taskHistory}
            onNewTask={handleNewTask}
            onDeleteTask={handleDeleteTask}
            onCreateProject={handleCreateProject}
            onMoveTaskToProject={handleMoveTaskToProject}
            onOpenSettings={() => setIsSettingsOpen(true)}
          />
          <SidebarInset className="flex flex-col bg-muted/30">
            {children}
          </SidebarInset>
          <SettingsDialog
            open={isSettingsOpen}
            onOpenChange={setIsSettingsOpen}
          />
        </div>
      </SidebarProvider>
    </LanguageProvider>
  );
}

export default ChatLayout;
