"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useT } from "@/app/i18n/client";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

import { useAutosizeTextarea } from "../hooks/use-autosize-textarea";
import { useTaskHistory } from "../hooks/use-task-history";
import { createMockProjects, createMockTaskHistory } from "../model/mocks";
import type { ProjectItem } from "../model/types";

import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { HomeHeader } from "./home-header";
import { TaskComposer } from "./task-composer";
import { ConnectorsBar } from "./connectors-bar";

import { SettingsDialog } from "@/components/settings/settings-dialog";

export function HomePage() {
  const { t } = useT("translation");
  const router = useRouter();

  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);

  const [projects, setProjects] = React.useState<ProjectItem[]>(() =>
    createMockProjects(t),
  );
  const { taskHistory, addTask, removeTask, moveTask } = useTaskHistory(() =>
    createMockTaskHistory(t),
  );

  const [inputValue, setInputValue] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  useAutosizeTextarea(textareaRef, inputValue);

  const handleNewTask = React.useCallback(() => {
    // Navigate to home for new task
    router.push("/");
  }, [router]);

  const handleOpenSettings = React.useCallback(() => {
    setIsSettingsOpen(true);
  }, []);

  const handleSendTask = React.useCallback(() => {
    if (!inputValue.trim()) return;

    // 1. Create a session ID
    const sessionId = Date.now().toString();

    // 2. Save prompt to localStorage for the chat session to pick up
    // Note: We need to ensure this code runs in client (which it does, inside callback)
    localStorage.setItem(`session_prompt_${sessionId}`, inputValue);

    // 3. Add to local history (optional, helps with instant feedback if we stay on page,
    // but we are navigating away. taskHistory in Home is local state, so it won't persist to ChatLayout
    // unless we persist it globally. For now, we follow the pattern.)
    addTask(inputValue, {
      timestamp: t("mocks.timestamps.justNow"),
      status: "running",
    });

    setInputValue("");

    // 4. Navigate to the chat page
    router.push(`/chat/${sessionId}`);
  }, [addTask, inputValue, t, router]);

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

  const handleRenameTask = React.useCallback(
    (taskId: string, newName: string) => {
      // TODO: Implement task rename logic
      console.log("Rename task:", taskId, "to:", newName);
    },
    [],
  );

  const handleMoveTaskToProject = React.useCallback(
    (taskId: string, projectId: string | null) => {
      moveTask(taskId, projectId);
    },
    [moveTask],
  );

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex min-h-svh w-full overflow-hidden bg-background">
        <AppSidebar
          projects={projects}
          taskHistory={taskHistory}
          onNewTask={handleNewTask}
          onDeleteTask={removeTask}
          onRenameTask={handleRenameTask}
          onMoveTaskToProject={handleMoveTaskToProject}
          onCreateProject={handleCreateProject}
          onOpenSettings={handleOpenSettings}
        />

        <SidebarInset className="flex flex-col bg-muted/30">
          <HomeHeader onOpenSettings={handleOpenSettings} />

          <div className="flex flex-1 flex-col items-center justify-center px-6 py-10">
            <div className="w-full max-w-2xl">
              {/* 欢迎语 */}
              <div className="mb-8 text-center">
                <h1 className="text-3xl font-medium tracking-tight text-foreground">
                  {t("hero.title")}
                </h1>
              </div>

              <TaskComposer
                textareaRef={textareaRef}
                value={inputValue}
                onChange={setInputValue}
                onSend={handleSendTask}
              />

              <ConnectorsBar />
            </div>
          </div>
        </SidebarInset>

        <SettingsDialog
          open={isSettingsOpen}
          onOpenChange={setIsSettingsOpen}
        />
      </div>
    </SidebarProvider>
  );
}
