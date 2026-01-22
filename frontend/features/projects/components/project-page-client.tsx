"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useT } from "@/lib/i18n/client";

import { useAutosizeTextarea } from "@/features/home/hooks/use-autosize-textarea";
import {
  createSessionAction,
  type CreateSessionInput,
} from "@/features/chat/actions/session-actions";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";

import { ProjectHeader } from "@/features/projects/components/project-header";
import { KeyboardHints } from "@/features/home/components/keyboard-hints";
import { QuickActions } from "@/features/home/components/quick-actions";
import {
  TaskComposer,
  type TaskSendOptions,
} from "@/features/home/components/task-composer";
import { useAppShell } from "@/components/shared/app-shell-context";

interface ProjectPageClientProps {
  projectId: string;
}

export function ProjectPageClient({ projectId }: ProjectPageClientProps) {
  const { t } = useT("translation");
  const router = useRouter();

  const { lng, projects, taskHistory, addTask, updateProject, deleteProject } =
    useAppShell();
  const currentProject = React.useMemo(
    () => projects.find((p: ProjectItem) => p.id === projectId) || projects[0],
    [projects, projectId],
  );

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  useAutosizeTextarea(textareaRef, inputValue);

  const focusComposer = React.useCallback(() => {
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleSendTask = React.useCallback(
    async (options?: TaskSendOptions) => {
      const inputFiles = options?.attachments ?? [];
      const mcpConfig = options?.mcp_config;
      if ((inputValue.trim() === "" && inputFiles.length === 0) || isSubmitting)
        return;

      setIsSubmitting(true);
      try {
        const config: CreateSessionInput["config"] = {};
        if (inputFiles.length > 0) {
          config.input_files = inputFiles;
        }
        if (mcpConfig && Object.keys(mcpConfig).length > 0) {
          config.mcp_config = mcpConfig;
        }

        const session = await createSessionAction({
          prompt: inputValue,
          projectId,
          config: Object.keys(config).length > 0 ? config : undefined,
        });

        localStorage.setItem(`session_prompt_${session.sessionId}`, inputValue);

        addTask(inputValue, {
          id: session.sessionId,
          timestamp: new Date().toISOString(),
          status: "running",
          projectId,
        });

        setInputValue("");

        router.push(`/${lng}/chat/${session.sessionId}`);
      } catch (error) {
        console.error("[Project] Failed to create session", error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [addTask, inputValue, isSubmitting, lng, projectId, router],
  );

  const handleQuickActionPick = React.useCallback(
    (prompt: string) => {
      setInputValue(prompt);
      focusComposer();
    },
    [focusComposer],
  );

  const handleRenameProject = React.useCallback(
    (targetProjectId: string, newName: string) => {
      updateProject(targetProjectId, { name: newName });
    },
    [updateProject],
  );

  const handleDeleteProject = React.useCallback(
    async (targetProjectId: string) => {
      await deleteProject(targetProjectId);
      if (targetProjectId === projectId) {
        router.push(`/${lng}/home`);
      }
    },
    [deleteProject, projectId, lng, router],
  );

  return (
    <>
      <ProjectHeader
        project={currentProject}
        onRenameProject={handleRenameProject}
        onDeleteProject={handleDeleteProject}
      />

      <div className="flex flex-1 flex-col items-center justify-center px-6 py-10">
        <div className="w-full max-w-2xl">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-medium tracking-tight text-foreground">
              {currentProject?.name || t("hero.title")}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {t("project.subtitle", {
                count: taskHistory.filter(
                  (task: TaskHistoryItem) => task.projectId === projectId,
                ).length,
              })}
            </p>
          </div>

          <TaskComposer
            textareaRef={textareaRef}
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSendTask}
            isSubmitting={isSubmitting}
          />

          <QuickActions onPick={handleQuickActionPick} />
          <KeyboardHints />
        </div>
      </div>
    </>
  );
}
